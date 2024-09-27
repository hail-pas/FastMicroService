import re
import uuid
from typing import TypeVar
from datetime import datetime
from collections import defaultdict

from fastapi import Body, Query, Depends, Request
from pydantic import BaseModel, ConfigDict, create_model
from pydantic.fields import FieldInfo
from tortoise.models import Model
from tortoise.queryset import QuerySet
from tortoise.exceptions import IntegrityError
from tortoise.expressions import Q
from tortoise.contrib.pydantic.base import PydanticModel

from conf.config import local_configs
from common.types import end_date_or_datetime, start_date_or_datetime
from common.schemas import CRUDPager
from common.pydantic import create_sub_fields_model
from common.responses import Resp
from services.exceptions import ApiException
from services.dependencies import paginate
from storages.clickhouse.connection import get_clickhouse_client

unique_error_msg_key_regex = re.compile(r"'(.*?)'")


ModelType = TypeVar("ModelType", bound=Model)

PydanticModelType = TypeVar("PydanticModelType", bound=PydanticModel)


def pagination_factory(
    db_model: type[ModelType],
    search_fields: set[str],
    order_fields: set[str],
    list_schema: type[PydanticModel],
    max_limit: int | None = None,
    param_type: type[Query] | type[Body] = Query,
) -> CRUDPager:
    return Depends(paginate(db_model, search_fields, order_fields, list_schema, max_limit, param_type))  # type: ignore


async def get_all(
    queryset: QuerySet[ModelType],  # type: ignore
    pagination: CRUDPager,
    *args: Q,
    **kwargs: dict,
) -> tuple[list, int]:  # type: ignore
    queryset = queryset.filter(*args).filter(**kwargs).order_by(*pagination.order_by)

    search = pagination.search
    if search and pagination.available_search_fields:
        sub_q_exps = []
        for search_field in pagination.available_search_fields:
            sub_q_exps.append(
                Q(**{f"{search_field}__icontains": search}),
            )
        q_expression = Q(*sub_q_exps, join_type=Q.OR)
        queryset = queryset.filter(q_expression)

    list_schema = pagination.list_schema
    if pagination.selected_fields:
        list_schema = create_sub_fields_model(  # type: ignore
            pagination.list_schema,
            pagination.selected_fields,
        )

    data = await list_schema.from_queryset(
        queryset.offset(pagination.offset).limit(pagination.limit),
    )
    total = await queryset.count()
    return data, total


async def obj_prefetch_fields(obj: Model, schema: type[PydanticModelType]) -> Model:
    db_model = obj.__class__
    _db2fields = defaultdict(list)
    for f in db_model._meta.fetch_fields.intersection(set(schema.model_fields.keys())):
        _db2fields[db_model._meta.fields_map[f].related_model._meta.db].append(f)  # type: ignore

    for db, fetch_fields in _db2fields.items():
        await obj.fetch_related(
            *fetch_fields,
            using_db=db,
        )
    return obj


async def kwargs_clean(
    data: dict,
    model: type[ModelType],
) -> tuple[dict, dict]:
    fields_map = model._meta.fields_map
    fk_fields = [f"{i}_id" for i in model._meta.fk_fields]
    m2m_fields = model._meta.m2m_fields

    simple_data = {}
    m2m_fields_data: dict = defaultdict(list)

    for key in data:
        if key not in fields_map:
            continue
        if key in fk_fields:
            if data[key]:
                field = fields_map[key.split("_id")[0]]
                obj = await field.related_model.get_or_none(  # type: ignore
                    **{field.to_field: data[key]},  # type: ignore
                )
                if not obj:
                    raise ApiException(
                        f"ID为{data[key]}的{field.description}不存在",
                    )
            simple_data[key] = data[key]
            continue

        if key in m2m_fields:
            if data[key] is None:
                m2m_fields_data[key] = None
                continue
            m2m_fields_data[key] = []
            field = fields_map[key]
            model = field.related_model  # type: ignore
            for related_id in data[key]:
                if isinstance(related_id, Model):
                    m2m_fields_data[key].append(obj)
                    continue
                obj = await model.get_or_none(
                    **{model._meta.pk_attr: related_id},
                )
                if not obj:
                    raise ApiException(
                        f"id为{related_id}的{model._meta.table_description}不存在",
                    )
                m2m_fields_data[key].append(obj)
            continue

        simple_data[key] = data[key]

    return simple_data, m2m_fields_data


async def create_obj(
    db_model: type[ModelType],
    data: dict,
) -> Model:
    data, m2m_data = await kwargs_clean(
        data,
        db_model,
    )

    try:
        obj = await db_model.create(**data)
    except IntegrityError as e:
        msg = e.args[0].args[1]
        if "Duplicate" in msg:
            msg_keys = unique_error_msg_key_regex.findall(msg)
            if (
                msg_keys
                and hasattr(db_model.Meta, "unique_error_messages")
                and db_model.Meta.unique_error_messages.get(msg_keys[-1])
            ):
                msg = db_model.Meta.unique_error_messages.get(msg_keys[-1])
            else:
                msg = f"{db_model._meta.table_description}已存在"
        raise ApiException(message=msg) from e

    for k, v in m2m_data.items():
        if v:
            await getattr(obj, k).add(*v)

    return obj


async def update_obj(
    obj: Model,
    queryset: QuerySet[ModelType],
    data: dict,
) -> Model:
    if not data:
        return obj

    db_model = obj.__class__
    data, m2m_data = await kwargs_clean(
        data,
        db_model,
    )

    if data:
        try:
            await queryset.filter(
                **{
                    db_model._meta.pk_attr: getattr(
                        obj,
                        db_model._meta.pk_attr,
                    ),
                },
            ).update(**data)
        except IntegrityError as e:
            msg = e.args[0].args[1]
            if "Duplicate" in msg:
                msg_keys = unique_error_msg_key_regex.findall(msg)
                if (
                    msg_keys
                    and hasattr(db_model.Meta, "unique_error_messages")
                    and db_model.Meta.unique_error_messages.get(msg_keys[-1])
                ):
                    msg = db_model.Meta.unique_error_messages.get(msg_keys[-1])
                else:
                    msg = f"{db_model._meta.table_description}已存在"
            raise ApiException(message=msg) from e
    for k, v in m2m_data.items():
        if v is None:
            continue
        await getattr(obj, k).clear()
        if not v:
            continue
        await getattr(obj, k).add(*v)
    await obj.refresh_from_db()
    return obj  # type: ignore


async def update_or_create_obj(
    db_model: type[ModelType],
    data: dict | None = None,
    instance: Model | None = None,
    pk: str | uuid.UUID | int | None = None,
) -> Resp[PydanticModelType] | Model:
    if not data:
        data = {}
    if pk or instance:
        if not instance:
            pk_field = db_model._meta.pk_attr
            obj = await db_model.get_or_none(**{pk_field: pk})
            if not obj:
                raise ApiException(f"主键为{pk}的{db_model._meta.table_description}对象不存在")
        else:
            obj = instance
        obj = await update_obj(obj, db_model.all(), data)
    else:
        obj = await create_obj(db_model, data)
    return obj


async def update(
    queryset: QuerySet[ModelType],
    id: str | uuid.UUID | int,
    data: dict,
    pydantic_model_type: type[PydanticModelType],
) -> Resp[PydanticModelType]:
    obj = await queryset.get_or_none(
        **{queryset.model._meta.pk_attr: id},
    )
    if not obj:
        raise ApiException("对象不存在")

    if data:
        obj = await update_obj(obj, queryset, data)  # type: ignore
    obj = await obj_prefetch_fields(obj, pydantic_model_type)  # type: ignore
    return Resp[PydanticModelType](data=await pydantic_model_type.from_tortoise_orm(obj))  # type: ignore


async def update_or_create(
    db_model: type[ModelType],
    pydantic_model_type: type[PydanticModelType],
    instance: Model | None = None,
    pk: str | uuid.UUID | int | None = None,
) -> Resp[PydanticModelType] | Model:
    data = pydantic_model_type.model_dump(exclude_unset=True)
    obj = await update_or_create_obj(db_model, data, instance, pk)
    obj = await obj_prefetch_fields(obj, pydantic_model_type)
    data = pydantic_model_type.model_validate(obj)
    return Resp[PydanticModelType](data=data)


class DeleteResp(BaseModel):
    deleted: int


async def delete(id: str | uuid.UUID | int, queryset: QuerySet[ModelType]) -> Resp[DeleteResp]:
    db_model = queryset.model
    db_model_label = db_model._meta.table_description
    if hasattr(db_model, "delte_by_ids"):
        r = await db_model.delte_by_ids([id])  # type: ignore
    else:
        r = await queryset.filter(
            **{db_model._meta.pk_attr: id},
        ).delete()
    if r < 1:
        return Resp.fail(message=f"{db_model_label}不存在或已被删除")
    return Resp[DeleteResp](data=DeleteResp(deleted=r))


async def batch_delete(
    queryset: QuerySet[ModelType],
    ids: set[str | uuid.UUID | int],
) -> Resp[DeleteResp]:
    db_model = queryset.model
    db_model_label = db_model._meta.table_description
    if hasattr(db_model, "delte_by_ids"):
        r = await db_model.delte_by_ids(ids)  # type: ignore
    else:
        r = await queryset.filter(
            id__in=ids,
        ).delete()
    if r < 1:
        return Resp.fail(message=f"{db_model_label}不存在或已被删除")
    return Resp[DeleteResp](data=DeleteResp(deleted=r))


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

VT = TypeVar("VT")

OT = TypeVar("OT")


class BaseFilterSchema(BaseModel):
    """
    字段的多运算符匹配, 生成相应sql
    >>> class MyFilterSchema(BaseFilterSchema):
    >>>     started_at: FilterUnit[str, Literal["="]] = Field(description="姓名, 完全匹配")
    >>>     age: FilterUnit[int, Literal["<", ">", "<=", ">="]] = Field(description="年龄")
    """

    @property
    def operator_sql_template(self) -> dict:
        return {
            "gt": "{field} > '{value}'",
            "gte": "{field} >= '{value}'",
            "lt": "{field} < '{value}'",
            "lte": "{field} <= '{value}'",
            "eq": "{field} = '{value}'",
            "neq": "{field} <> '{value}'",
            "isnull": "{field} is null",
            "isnotnull": "{field} is not null",
            "in": "{field} in ({value})",
            "like": "{field} like '%{value}%'",
            "not_like": "{field} not like '%{value}%'",
            "left_like": "{field} like '{value}%'",
            "right_like": "{field} like '%{value}'",
        }

    model_config = ConfigDict()

    def get_sql(self, request: Request | None, field_prefix: str = "") -> str:
        sql = ""

        filter_schema = self.model_dump()
        for field, filter_config in filter_schema.items():
            if filter_config:
                for operator, value in filter_config.items():
                    if value is None:
                        continue

                    if sql:
                        sql += " AND "

                    if operator == "isnull" and not value:
                        operator = "isnotnull"  # ruff: noqa: PLW2901
                    elif operator == "isnotnull" and not value:
                        operator = "isnull"  # ruff: noqa: PLW2901

                    if isinstance(value, bool) and operator not in ["isnull", "isnotnull"]:
                        sql += "{field} = {value}".format(
                            field=f"{field_prefix}{field}",
                            value=int(value),
                        )
                    else:
                        sql += self.operator_sql_template[operator].format(
                            field=f"{field_prefix}{field}",
                            value=value,
                        )

        return "WHERE 1=1" if not sql else f"WHERE {sql}"


FilterType = TypeVar("FilterType", bound=BaseFilterSchema)


def create_sql_filter_schema(
    name: str,
    **fields,
) -> type[FilterType]:
    model_fields: dict[str, FieldInfo] = {}

    for field_name, field_type in fields.items():
        field_model_fields = {}

        for k in field_type.__args__[0].__args__:
            k_type = field_type.__args__[1]
            if k in ["isnull", "isnotnull"]:
                k_type = bool

            elif k_type is datetime and k in [">", ">="]:
                k_type = start_date_or_datetime

            elif k_type is datetime and k in ["<", "<="]:
                k_type = end_date_or_datetime

            field_model_fields[f"{k}"] = (k_type | None, FieldInfo(default=None, annotation=k_type | None))

        mf_type = create_model(f"name{field_name.title()}", **field_model_fields) | None
        model_fields[field_name] = (mf_type, FieldInfo(default=None, annotation=mf_type))

    return create_model(
        name,
        __base__=BaseFilterSchema,
        **model_fields,
    )


async def get_clickhouse_all(
    request: Request,
    model: type[BaseModel],
    table_name: str,
    filter_schema: FilterType,
    pager: CRUDPager,
) -> tuple[int, list]:
    selected_fields = pager.selected_fields
    if not selected_fields:
        selected_fields = set(model.model_fields.keys())
        list_schema = pager.list_schema
    else:
        list_schema = create_sub_fields_model(
            pager.list_schema,
            selected_fields,
        )

    field_prefix = ""

    perm_filters = await request.user.get_role_vehicle_perm_filter_kwargs()

    if perm_filters and "vehicle_id" in selected_fields:
        field_prefix = "l."
        table_name = (
            f"{table_name} as l inner join {local_configs.clickhouse.tables.vehicle} as v on l.vehicle_id = v.id"
        )
    fields_query = ", ".join([f"{field_prefix}{i}" for i in selected_fields])

    query = "SELECT {fields_query} FROM " + table_name + " {where_query}"

    order_limit_query = ""
    if pager.order_by:
        order_limit_query += ", ".join(
            [
                f"{field_prefix}{order_by.split('-', 1)[-1]} {'DESC' if order_by.startswith('-') else 'ASC'}"
                for order_by in pager.order_by
            ],
        )
        order_limit_query = f" ORDER BY {order_limit_query}"

    order_limit_query += f" LIMIT {pager.limit} OFFSET {pager.offset}"

    where_query = filter_schema.get_sql(request)

    if field_prefix:
        perm_where_query = " "
        for k, v in perm_filters.items():
            if not v:
                continue
            match k:
                case "release_city_id__in":
                    perm_where_query += f" AND v.release_city_id in ({','.join(map(str, v))})"
                case "energy_type__in":
                    v = [f"'{i}'" for i in v]
                    perm_where_query += f" AND v.energy_type in ({','.join(v)})"
                case "device_type__in":
                    v = [f"'{i}'" for i in v]
                    perm_where_query += f" AND v.device_type in ({','.join(v)})"

        where_query += perm_where_query

    print(">" * 100, query.format(fields_query=fields_query, where_query=where_query) + order_limit_query)
    async with get_clickhouse_client(
        url=local_configs.clickhouse.url,
        username=local_configs.clickhouse.username,
        password=local_configs.clickhouse.password,
    ) as client:
        total = (await client.fetchrow(query.format(fields_query="count(*)", where_query=where_query))).get("count()")
        if not total:
            return total, []

        data = [
            list_schema(**row)
            for row in await client.fetch(
                (query.format(fields_query=fields_query, where_query=where_query) + order_limit_query).format(
                    selected_fields=selected_fields,
                ),
            )
        ]

    return total, data
