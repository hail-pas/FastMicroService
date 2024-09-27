from typing import Annotated
from collections.abc import Callable

from jose import JWTError, ExpiredSignatureError, jwt
from loguru import logger
from fastapi import Body, Query, Depends, Request
from pydantic import PositiveInt
from cachetools import TTLCache
from jose.exceptions import JWTClaimsError
from tortoise.models import Model
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from tortoise.contrib.pydantic import PydanticModel

from conf.config import local_configs
from common.enums import ResponseCodeEnum
from common.encrypt import JwtUtil
from common.schemas import Pager, CRUDPager
from services.exceptions import ApiException
from common.constant.messages import (
    AuthorizationHeaderInvalidMsg,
    AuthorizationHeaderMissingMsg,
    AuthorizationHeaderTypeErrorMsg,
)
from storages.relational.models.account import Account
from storages.relational.schema.account import JwtPayload


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


def pure_get_pager(
    page: PositiveInt = Query(default=1, example=1, description="第几页"),
    size: PositiveInt = Query(default=10, example=10, description="每页数量"),
) -> Pager:
    return Pager(limit=size, offset=(page - 1) * size)


def paginate(
    model: type[Model],
    search_fields: set[str],
    order_fields: set[str],
    list_schema: type[PydanticModel],
    max_limit: int | None,
    param_type: type[Query] | type[Body] = Query,
) -> Callable[[PositiveInt, PositiveInt, str, set[str], set[str] | None], CRUDPager]:
    def get_pager(
        page: PositiveInt = param_type(default=1, example=1, description="第几页"),
        size: PositiveInt = param_type(default=10, example=10, description="每页数量"),
        search: str = param_type(
            None,
            description="搜索关键字."
            + (f" 匹配字段: {', '.join(search_fields)}" if search_fields else "无可匹配的字段"),  # ruff: noqa: E501
        ),
        order_by: set[str] = param_type(
            default=set(),
            # example="-id",
            description=(
                "排序字段. 升序保持原字段名, 降序增加前缀-."
                + (f" 可选字段: {', '.join(order_fields)}" if order_fields else " 无可排序字段")  # ruff: noqa: E501
            ),
        ),
        selected_fields: set[str] = param_type(
            default=set(),
            description=f"指定返回字段. 可选字段: {', '.join(list_schema.model_fields.keys())}",
        ),
    ) -> CRUDPager:
        if max_limit is not None:
            size = min(size, max_limit)
        for field in order_by:
            if field.startswith("-"):
                field = field[1:]  # noqa

            if hasattr(model, "model_fields"):
                available_order_fields = model.model_fields.keys()
            else:
                available_order_fields = model._meta.db_fields

            if field not in available_order_fields:
                raise ApiException(
                    "排序字段不存在",
                )
        if selected_fields:
            selected_fields.add("id")

        if page <= 0:
            raise ApiException(
                "页码必须大于0",
            )
        if size <= 0:
            raise ApiException(
                "每页数量必须大于0",
            )
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


_account_cache = TTLCache(maxsize=256, ttl=60 * 60)


async def _get_account_by_username(username: str) -> Account:
    if username in _account_cache:
        return _account_cache[username]
    acc = await Account.get_or_none(username=username, deleted_at=0)
    if not acc:
        raise ApiException(
            code=ResponseCodeEnum.unauthorized,
            message="Invalid Account",
        )
    _account_cache[username] = acc
    return acc


async def _validate_jwt_token(
    request: Request,
    token: HTTPAuthorizationCredentials,
) -> Account:
    try:
        token_value = token.credentials
        kid = jwt.get_unverified_header(token_value).get("kid", "rsa1")
        jwk = JwtUtil.get_jwk_by_kid(kid, {})
        if not jwk:
            logger.info(f"Invalid Token: No matching kid = {kid} found in jwk set")
            raise ApiException(message="Invalid Token", code=ResponseCodeEnum.unauthorized)
        payload = JwtUtil[JwtPayload].decode(
            JwtPayload,
            token_value,
            jwk,
            audience=local_configs.third.xsso.client_id,
        )
    except (JWTError, ExpiredSignatureError, JWTClaimsError) as e:
        logger.info(f"Invalid Token: {e}")
        raise ApiException(
            code=ResponseCodeEnum.unauthorized,
            message="Invalid Token",
        ) from e

    account = await _get_account_by_username(payload.username)

    if not account:
        raise ApiException(
            code=ResponseCodeEnum.unauthorized,
            message="Invalid Account",
        )

    # set scope
    request.scope["user"] = account
    return account


class TokenRequired:
    # def __init__(
    #     self,
    # ) -> None:
    #     ...

    async def __call__(
        self,
        request: Request,  # WebSocket
        token: Annotated[HTTPAuthorizationCredentials, Depends(auth_schema)],
    ) -> Account:
        return await _validate_jwt_token(
            request,
            token,
            # self.user_center_redis_conn_pool,
        )


token_required = TokenRequired()


class ApiPermissionCheck:
    def __init__(
        self,
    ) -> None:
        pass

    async def __call__(
        self,
        request: Request,
        token: Annotated[HTTPAuthorizationCredentials, Depends(auth_schema)],
    ) -> Account:
        account: Account | None = request.scope.get("user")  # type: ignore
        if not account:
            account = await token_required(request, token)

        if account.is_super_admin:
            return account

        method = request.method
        root_path: str = request.scope["root_path"]
        path: str = request.scope["route"].path

        if await account.has_permission(
            [
                "*",
                f"{request.app.code}:*",
                f"{request.app.code}:{method}:{root_path}{path}",
            ],
        ):
            return account

        raise ApiException(
            code=ResponseCodeEnum.forbidden.value,
            message=ResponseCodeEnum.forbidden.label,
        )


api_permission_check = ApiPermissionCheck()
