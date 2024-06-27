from typing import Generic, TypeVar, Annotated
from collections.abc import Callable, Awaitable

from fastapi import Query, Depends, Request, Security
from pydantic import PositiveInt
from tortoise.models import Model
from fastapi.security import HTTPBearer, APIKeyHeader, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from tortoise.contrib.pydantic import PydanticModel

from common.enums import ResponseCodeEnum
from common.schemas import CRUDPager
from services.exceptions import ApiException
from common.constant.messages import (
    ApikeyMissingMsg,
    AuthorizationHeaderInvalidMsg,
    AuthorizationHeaderMissingMsg,
    AuthorizationHeaderTypeErrorMsg,
)

T = TypeVar("T")


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


class TheBearer(HTTPBearer):
    async def __call__(
        self: "TheBearer",
        request: Request,  # WebSocket
    ) -> HTTPAuthorizationCredentials:  # _authorization: Annotated[Optional[str], Depends(oauth2_scheme)]
        authorization: str | None = request.headers.get("Authorization")
        if not authorization:
            raise ApiException(
                code=ResponseCodeEnum.unauthorized,
                message=AuthorizationHeaderMissingMsg,
            )
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            raise ApiException(
                code=ResponseCodeEnum.unauthorized,
                message=AuthorizationHeaderInvalidMsg,
            )
        if scheme != "Bearer" and self.auto_error:
            raise ApiException(
                code=ResponseCodeEnum.unauthorized,
                message=AuthorizationHeaderTypeErrorMsg,
            )
        return HTTPAuthorizationCredentials(
            scheme=scheme,
            credentials=credentials,
        )


auth_schema = TheBearer()


class JwtTokenRequired(Generic[T]):
    """完全自定义校验"""

    validator: Callable[
        [Request, HTTPAuthorizationCredentials],
        Awaitable[T],
    ]

    def __init__(
        self,
        validator: Callable[
            [Request, HTTPAuthorizationCredentials],
            Awaitable[T],
        ],
    ) -> None:
        self.validator = validator  # type: ignore

    async def __call__(
        self,
        request: Request,
        token: Annotated[HTTPAuthorizationCredentials, Depends(auth_schema)],
    ) -> T:
        return await self.validator(request, token)


class ApiKeyRequired(Generic[T]):
    validator: Callable[[Request, str], Awaitable[T]]

    def __init__(
        self,
        validator: Callable[[Request, str], Awaitable[T]],
    ) -> None:
        self.validator = validator

    async def __call__(
        self,
        request: Request,
        api_key: str = Security(
            APIKeyHeader(
                name="X-Api-Key",
                scheme_name="API key header",
                auto_error=False,
            ),
        ),
    ) -> T:
        if not api_key:
            raise ApiException(
                message=ApikeyMissingMsg,
                code=ResponseCodeEnum.unauthorized,
            )

        return await self.validator(request, api_key)
