import traceback
from typing import Any
from collections.abc import Callable

import orjson
from fastapi import WebSocket
from pydantic import ValidationError as PydanticValidationError
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from tortoise.exceptions import ValidationError as TortoiseValidationError
from starlette.exceptions import HTTPException

from conf.config import local_configs
from common.responses import Resp, AesResponse, ResponseCodeEnum
from common.constant.messages import (
    ValidateFailedMsg,
    ValidationErrorMsgTemplates,
    DirectValidateErrorMsgTemplates,
)


class ApiException(Exception):
    """非 0 的业务错误."""

    code: ResponseCodeEnum = ResponseCodeEnum.failed
    message: str

    def __init__(
        self,
        message: str,
        code: ResponseCodeEnum = ResponseCodeEnum.failed,
    ) -> None:
        self.code = code
        self.message = message


class ValidationError(Exception):
    """自定义校验异常
    1. 覆盖tortoise Validation Error, 用于自定义提示语
    """

    error_type: str
    error_message_template: str
    ctx: dict  # value

    def __init__(
        self,
        error_type: str,
        error_message_template: str,
        ctx: dict,
    ) -> None:
        self.error_type = error_type
        self.error_message_template = error_message_template
        self.ctx = ctx

    def __str__(self) -> str:
        msg = self.error_message_template.format(**self.ctx)
        field_name = self.ctx.get("field_name")
        if field_name:
            msg = f"{field_name}: {msg}"
        return msg


async def api_exception_handler(
    request: Request | WebSocket,
    exc: ApiException,
) -> AesResponse:
    return AesResponse(
        content=Resp(
            code=exc.code,
            message=exc.message,
            data=None,
        ).model_dump(),
    )


async def unexpected_exception_handler(
    request: Request | WebSocket,
    exc: Exception,
) -> AesResponse | HTMLResponse:
    if local_configs.project.debug:
        return HTMLResponse(
            content=traceback.format_exc(),
            headers=local_configs.server.cors.headers,
        )

    return AesResponse(
        content=Resp(
            code=ResponseCodeEnum.internal_error.value,
            message=ResponseCodeEnum.internal_error.label,
            data=None,
        ).model_dump(),
        headers=local_configs.server.cors.headers,
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> AesResponse:
    """HttpException 状态码非 200 的错误
    :param request:
    :param exc:
    :return:
    """
    return AesResponse(
        content=Resp(
            code=exc.status_code,
            message=exc.detail,
            data=None,
        ).model_dump(),
    )


def get_exc_field_msg(
    exc: RequestValidationError | PydanticValidationError,
) -> tuple[str, str]:
    error_list = exc.errors()
    try:
        first_error_info = error_list[0]
        error_type = first_error_info["type"]
        if error_type in DirectValidateErrorMsgTemplates:
            # 固定异常
            field_name, msg = DirectValidateErrorMsgTemplates[error_type]
        else:
            # 字段异常
            error = exc.raw_errors[0]  # type: ignore
            model = getattr(error.exc, "model", None)  # type: ignore
            if len(first_error_info["loc"]) == 2:
                field_name = str(first_error_info["loc"][1])
            elif len(first_error_info["loc"]) > 2:
                field_name = str(first_error_info["loc"][-1])
            else:
                field_name = str(first_error_info["loc"][0])
            field_name = field_name.split(",", 1)[0]  # type: ignore
            if model:
                fields: dict = model.__fields__
                if field_name in fields:
                    field_name = fields[field_name].field_info.description or field_name
            ctx = first_error_info.get("ctx", {})
            msg = first_error_info["msg"]
            if error_type in ValidationErrorMsgTemplates:
                msg = ValidationErrorMsgTemplates[error_type].format(**ctx)

            if error_type == "type_error.enum":  # enum类型的 ast.literal 有问题
                error_list = None  # type: ignore
    except Exception:  # type: ignore
        error_exc_data = orjson.loads(exc.json())  # type: ignore
        field_name = error_exc_data[0]["loc"][0]
        msg = error_exc_data[0]["msg"]
    return field_name, msg


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> AesResponse:
    """参数校验错误."""
    # try:
    #     error = exc.raw_errors[0]
    #     error_exc = error.exc
    #     error_exc_data = orjson.loads(error_exc.json())
    #     field_name = error_exc_data[0]["loc"][0]
    #     model = error_exc.model
    #     fields: dict = model.__fields__
    #     if field_name in fields:
    #         field_name = (
    #             fields[field_name].field_info.description or field_name
    #         )
    #     error_type = error_exc_data[0]["type"]
    #     ctx = error_exc_data[0].get("ctx") or {}
    #     msg = (
    #         ValidationErrorMsgTemplates[error_type].format(**ctx)
    #         if error_type in ValidationErrorMsgTemplates
    #         else error_exc_data[0]["msg"]
    #     )
    # except AttributeError:
    #     error_exc_data = orjson.loads(exc.json())
    #     field_name = error_exc_data[0]["loc"][0]
    #     msg = error_exc_data[0]["msg"]

    # model description 取首部分
    # field_name = field_name.split(",", 1)[0]  # type: ignore
    if not isinstance(exc, RequestValidationError):
        # field_name = f"Backend-{field_name}"
        raise exc

    field_name, msg = get_exc_field_msg(exc)

    return AesResponse(
        content=Resp(
            code=ResponseCodeEnum.failed,
            message=f"{field_name}: {msg}",
            data=None,  # {"data": exc.body, "errors": error_list},
        ).model_dump(),
    )


async def custom_validation_error_handler(
    request: Request,
    exc: ValidationError,
) -> AesResponse:
    message = exc.error_message_template.format(**exc.ctx)
    if "field_name" in exc.ctx:
        message = f"{exc.ctx['field_name']}: {message}"

    return AesResponse(
        content=Resp(
            code=ResponseCodeEnum.failed,
            message=message,
        ).model_dump(),
    )


async def tortoise_validation_error_handler(
    request: Request,
    exc: TortoiseValidationError,
) -> AesResponse:
    field_name = exc.args[0].split(":")[0]

    return AesResponse(
        content=Resp(
            code=ResponseCodeEnum.failed,
            message=f"{field_name}: {ValidateFailedMsg % ''}",
        ).model_dump(),
    )


roster: list[tuple[type[Exception], Callable[..., Any]]] = [
    (RequestValidationError, validation_exception_handler),
    (PydanticValidationError, validation_exception_handler),
    (ValidationError, custom_validation_error_handler),
    (TortoiseValidationError, tortoise_validation_error_handler),
    (ApiException, api_exception_handler),
    (HTTPException, http_exception_handler),
    (Exception, unexpected_exception_handler),
]
