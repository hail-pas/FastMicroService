import re
import uuid
from typing import TypeVar
from collections import defaultdict

from fastapi import Depends
from pydantic import BaseModel
from tortoise.models import Model
from tortoise.queryset import QuerySet
from tortoise.exceptions import IntegrityError
from tortoise.expressions import Q
from tortoise.contrib.pydantic.base import PydanticModel

from common.schemas import CRUDPager
from common.pydantic import create_sub_fields_model
from common.responses import Resp, PageData
from services.exceptions import ApiException
from services.dependencies import paginate

unique_error_msg_key_regex = re.compile(r"'(.*?)'")


ModelT = TypeVar("ModelT", bound=Model)

PydanticModelT = TypeVar("PydanticModelT", bound=PydanticModel)


def pagination_factory(
    db_model: type[Model],
    search_fields: set[str],
    order_fields: set[str],
    list_schema: type[PydanticModel],
    max_limit: int | None = None,
) -> CRUDPager:
    return Depends(paginate(db_model, search_fields, order_fields, list_schema, max_limit))  # type: ignore


async def get_all(
    queryset: QuerySet[ModelT],  # type: ignore
    pagination: CRUDPager,
    *args: Q,
    **kwargs: dict,
) -> Resp[PageData]:  # type: ignore
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
    return Resp[PageData[list_schema]](  # type: ignore
        data=PageData[list_schema](records=data, total_count=total, pager=pagination),  # type: ignore
    )


async def obj_prefetch_fields(obj: ModelT, schema: type[PydanticModelT]) -> ModelT:
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
    model: type[Model],
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
    db_model: type[ModelT],
    data: dict,
) -> ModelT:
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
    obj: ModelT,
    queryset: QuerySet[ModelT],
    data: dict,
) -> ModelT:
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


async def update(
    queryset: QuerySet[ModelT],
    id: str | uuid.UUID | int,
    data: dict,
    pydantic_model_type: type[PydanticModelT],
) -> Resp[PydanticModelT]:
    obj = await queryset.get_or_none(
        **{queryset.model._meta.pk_attr: id},
    )
    if not obj:
        raise ApiException("对象不存在")

    if data:
        obj = await update_obj(obj, queryset, data)  # type: ignore
    obj = await obj_prefetch_fields(obj, pydantic_model_type)  # type: ignore
    return Resp[PydanticModelT](data=pydantic_model_type.model_validate(obj))  # type: ignore


class DeleteResp(BaseModel):
    deleted: int


async def delete(id: str | uuid.UUID | int, queryset: QuerySet[Model]) -> Resp[DeleteResp]:
    db_model = queryset.model
    db_model_label = db_model._meta.table_description
    if hasattr(db_model, "delte_by_ids"):
        r = await db_model.delte_by_ids([id])
    else:
        r = await queryset.filter(
            **{db_model._meta.pk_attr: id},
        ).delete()
    if r < 1:
        return Resp.fail(message=f"{db_model_label}不存在或已被删除")
    return Resp[DeleteResp](data=DeleteResp(deleted=r))


async def batch_delete(
    queryset: QuerySet[Model],
    ids: set[str | uuid.UUID | int],
) -> Resp[DeleteResp]:
    db_model = queryset.model
    db_model_label = db_model._meta.table_description
    if hasattr(db_model, "delte_by_ids"):
        r = await db_model.delte_by_ids(ids)
    else:
        r = await queryset.filter(
            id__in=ids,
        ).delete()
    if r < 1:
        return Resp.fail(message=f"{db_model_label}不存在或已被删除")
    return Resp[DeleteResp](data=DeleteResp(deleted=r))
