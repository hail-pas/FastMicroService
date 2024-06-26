from collections.abc import Callable

from fastapi import Query
from pydantic import PositiveInt
from tortoise.models import Model
from tortoise.contrib.pydantic import PydanticModel

from common.schemas import CRUDPager
from services.exceptions import ApiException


def paginate(
    model: type[Model],
    search_fields: set[str],
    order_fields: set[str],
    list_schema: type[PydanticModel],
    max_limit: int | None,
) -> Callable[[PositiveInt, PositiveInt, str, set[str], set[str] | None], CRUDPager]:
    def get_pager(
        page: PositiveInt = Query(default=1, example=1, description="第几页"),
        size: PositiveInt = Query(default=10, example=10, description="每页数量"),
        search: str = Query(
            None,
            description="搜索关键字."
            + (f" 匹配字段: {', '.join(search_fields)}" if search_fields else "无可匹配的字段"),  # ruff: noqa: E501
        ),
        order_by: set[str] = Query(
            default=set(),
            # example="-id",
            description=(
                "排序字段. 升序保持原字段名, 降序增加前缀-."
                + (f" 可选字段: {', '.join(order_fields)}" if order_fields else " 无可排序字段")  # ruff: noqa: E501
            ),
        ),
        selected_fields: set[str]
        | None = Query(
            default=set(),
            description=f"指定返回字段. 可选字段: {', '.join(list_schema.model_fields.keys())}",
        ),
    ) -> CRUDPager:
        if max_limit is not None:
            size = min(size, max_limit)
        for field in order_by:
            if field.startswith("-"):
                field = field[1:]  # noqa
            if field not in model._meta.db_fields:
                raise ApiException(
                    "排序字段不存在",
                )
        if selected_fields:
            selected_fields.add("id")
        return CRUDPager(
            limit=size,
            offset=(page - 1) * size,
            order_by=set(
                filter(lambda i: i.split("-")[-1] in order_fields, order_by),
            ),
            search=search,
            selected_fields=selected_fields,
            available_search_fields=search_fields,
            list_schema=list_schema,
        )

    return get_pager
