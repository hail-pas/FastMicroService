# ruff: noqa: RET504
from math import ceil
from typing import Self, Generic, TypeVar
from datetime import datetime
from collections.abc import Sequence

from pydantic import Field, BaseModel, field_validator, model_validator
from fastapi.responses import ORJSONResponse
from starlette_context import context

from common.enums import ResponseCodeEnum
from common.utils import datetime_now
from common.context import ContextKeyEnum
from common.schemas import Pager


class AesResponse(ORJSONResponse):
    pass

    # def render(self, content: dict) -> bytes:
    #     """AES加密响应体"""
    #     # if not get_settings().DEBUG:
    #     # content = AESUtil(local_configs.AES.SECRET).encrypt_data(
    #     #       orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS).decode())
    #     return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS)


DataT = TypeVar("DataT")


class Resp(BaseModel, Generic[DataT]):
    """响应Model."""

    code: int = Field(
        default=ResponseCodeEnum.success,
        description=f"业务响应代码, {ResponseCodeEnum._dict}",  # type: ignore
    )
    response_time: datetime | None = Field(default_factory=datetime_now, description="响应时间")
    message: str | None = Field(default=None, description="响应提示信息")
    data: DataT | None = Field(
        default=None,
        description="响应数据格式",
    )
    trace_id: str | None = Field(default=None, description="请求唯一标识")

    @field_validator("trace_id", mode="before")
    def set_trace_id(cls, value: str | None) -> str:
        if not value:
            value = str(context.get(ContextKeyEnum.request_id.value, ""))
        return value

    @model_validator(mode="after")
    def set_failed_response(self) -> Self:
        context[ContextKeyEnum.response_code.value] = self.code
        if self.code != ResponseCodeEnum.success:
            context[ContextKeyEnum.response_data.value] = {
                "code": self.code,
                "message": self.message,
                "data": self.data,
            }
        return self

    # model_config = ConfigDict(json_encoders={datetime: lambda v: v.strftime(DATETIME_FORMAT_STRING)})

    @classmethod
    def fail(
        cls,
        message: str,
        code: int = ResponseCodeEnum.failed.value,
    ) -> Self:
        return cls(code=code, message=message)


class SimpleSuccess(Resp):
    """简单响应成功."""


class PageInfo(BaseModel):
    """翻页相关信息."""

    total_page: int
    total_count: int
    size: int
    page: int


class PageResp(BaseModel, Generic[DataT]):
    page_info: PageInfo
    records: Sequence[DataT]


def generate_page_info(total_count: int, pager: Pager) -> PageInfo:
    return PageInfo(
        total_page=ceil(total_count / pager.limit),
        total_count=total_count,
        size=pager.limit,
        page=pager.offset // pager.limit + 1,
    )
