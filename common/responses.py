# ruff: noqa: RET504
from math import ceil
from typing import Generic, TypeVar
from datetime import datetime

import orjson
from pydantic import Field, BaseModel, validator, root_validator
from pydantic.generics import GenericModel
from starlette_context import context
from starlette.responses import JSONResponse

from common.enums import ResponseCodeEnum
from common.utils import DATETIME_FORMAT_STRING, datetime_now
from common.context import ContextKeyEnum
from common.schemas import Pager
from common.pydantic import DateTimeFormatConfig


class AesResponse(JSONResponse):
    """响应：
    res = {
        "code": 0,
        "response_time": "datetime",
        "message": "message",  # 可选信息
        "data": "data"    # 当code等于0表示正常调用，该字段返回正常结果
        "trace_id": "trace_id"  # 请求唯一标识
        }
    不直接使用该Response， 使用下面的响应Model - 具有校验/生成文档的功能.
    """

    def render(self, content: dict) -> bytes:
        """AES加密响应体"""
        # if not get_settings().DEBUG:
        # content = AESUtil(local_configs.AES.SECRET).encrypt_data(
        #       orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS).decode())
        return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS)


DataT = TypeVar("DataT")


class BaseResp(GenericModel, Generic[DataT]):
    """响应Model."""

    code: int = Field(
        default=ResponseCodeEnum.success.value,
        description=f"业务响应代码, {ResponseCodeEnum.dict}",  # type: ignore
    )
    response_time: datetime | None = Field(default=None, description="响应时间")
    message: str | None = Field(default=None, description="响应提示信息")
    trace_id: str | None = Field(default=None, description="请求唯一标识")

    @validator("response_time", always=True)
    def set_response_time(cls, value: datetime | None) -> str:
        if not value:
            value = datetime_now()
        return value.strftime(DATETIME_FORMAT_STRING)

    @validator("trace_id", always=True)
    def set_trace_id(cls, value: str | None) -> str:
        if not value:
            value = str(context.get(ContextKeyEnum.request_id.value, ""))
        return value

    @root_validator
    def set_failed_response(cls, values: dict) -> dict:
        code = values["code"]
        context[ContextKeyEnum.response_code.value] = code
        if code != ResponseCodeEnum.success.value:
            context[ContextKeyEnum.response_data.value] = {
                "code": code,
                "message": values["message"],
                "data": values["data"],
            }
        return values

    class Config(DateTimeFormatConfig):
        ...


class Resp(BaseResp[DataT], Generic[DataT]):
    data: DataT | None = Field(
        default=None,
        description="响应数据格式",
    )

    @classmethod
    def fail(
        cls,
        message: str,
        code: int = ResponseCodeEnum.failed.value,
    ) -> "Resp":
        return cls(code=code, message=message)


class SimpleSuccess(Resp):
    """简单响应成功."""


class PageInfo(BaseModel):
    """翻页相关信息."""

    total_page: int
    total_count: int
    size: int
    page: int


# class PageResp(BaseResp[DataT], Generic[DataT]):
#     page_info: PageInfo
#     data: Sequence[DataT]

#     __params_type__ = Pager


def generate_page_info(total_count: int, pager: Pager) -> PageInfo:
    return PageInfo(
        total_page=ceil(total_count / pager.limit),
        total_count=total_count,
        size=pager.limit,
        page=pager.offset // pager.limit + 1,
    )
