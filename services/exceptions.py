import traceback
from typing import Any
from collections.abc import Callable

from fastapi import WebSocket
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.exceptions import HTTPException

from conf.config import local_configs
from common.responses import Resp, AesResponse, ResponseCodeEnum
from common.exceptions import ApiException, ValidationError
from common.constant.validate import (
    ValidationErrorMsgTemplates,
    DirectValidateErrorMsgTemplates,
)


async def api_exception_handler(
    request: Request | WebSocket,
    exc: ApiException,
) -> AesResponse:
    return AesResponse(
        content=Resp(
            code=exc.code,
            message=exc.message,
            data=None,
        ).model_dump_json(),
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
        ).model_dump_json(),
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
        ).model_dump_json(),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> AesResponse:
    """参数校验错误."""

    error = exc.errors()[0]
    error_type = error["type"]
    ctx = error.get("ctx", {})

    field_name = error["loc"][0] if len(error["loc"]) == 1 else ".".join([str(i) for i in error["loc"][1:]])

    if error_type in DirectValidateErrorMsgTemplates:
        field_name, message = DirectValidateErrorMsgTemplates[error_type]
        message = message.format(**ctx)
    else:
        message = ValidationErrorMsgTemplates[error_type]
        message = message.format(**ctx)

    return AesResponse(
        content=Resp(
            code=ResponseCodeEnum.failed,
            message=f"{field_name}: {message}",
            data=exc.errors(),  # {"data": exc.body, "errors": error_list},
        ).model_dump_json(),
    )


def get_validation_text(exc: RequestValidationError, pyd: BaseModel) -> str:
    error = exc.errors()[0]
    error_type = error["type"]
    ctx = error.get("ctx", {})

    if len(error["loc"]):
        field_name = error["loc"][0]
    else:
        field_name = ".".join([str(i) for i in error["loc"][1:]])

    if error_type in DirectValidateErrorMsgTemplates:
        field_name, message = DirectValidateErrorMsgTemplates[error_type]
        message = message.format(**ctx)
    else:
        message = ValidationErrorMsgTemplates[error_type]
        message = message.format(**ctx)
    field_info = pyd.model_fields.get(field_name)
    if hasattr(field_info, "description"):
        return f"{field_info.description}错误"
        # return f"{field_info.description}({field_name}): {message}"
    return f"{field_name}错误"


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
        ).model_dump_json(),
    )


roster: list[tuple[type[Exception], Callable[..., Any]]] = [
    (RequestValidationError, validation_exception_handler),
    # (PydanticValidationError, validation_exception_handler),
    (ValidationError, custom_validation_error_handler),
    # (TortoiseValidationError, tortoise_validation_error_handler),
    (ApiException, api_exception_handler),
    (HTTPException, http_exception_handler),
    (Exception, unexpected_exception_handler),
]
