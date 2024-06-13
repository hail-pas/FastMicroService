import abc
import datetime
import warnings
from typing import Any, TypeVar
from urllib.parse import urlparse
from collections.abc import Callable

from tortoise import fields, timezone, validators
from tortoise.models import Model
from tortoise.timezone import get_use_tz, get_default_timezone

# from burnish_sdk_py.common.regexes import URI_REGEX


class StorageMixin:
    @abc.abstractmethod
    def get_full_path(
        self,
        path: str,
        expire: int | None = None,
    ) -> tuple[bool, str]:
        ...

    def get_stored_path(
        self,
        url: str,
    ) -> str:
        return urlparse(url).path
        # if not url.startswith("http"):
        #     return url
        # try:
        #     return URI_REGEX.match(url).group(1)  # type: ignore
        # except Exception:
        #     return url


StorageType = TypeVar("StorageType", bound=StorageMixin)


class FileField(fields.CharField):
    """
    OSS文件字段
    """

    _file_storage: StorageMixin
    _expire: int | None
    _extensions: list[str] | None

    def __init__(
        self,
        max_length: int,
        storage: StorageType,
        extensions: list[str] | None = None,
        expire: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(max_length=max_length, **kwargs)
        self._file_storage = storage
        self._expire = expire
        self._extensions = extensions

    def to_db_value(self, value: str, instance: "FileField") -> str:  # type: ignore
        if not value:
            return ""
        if value.startswith("http"):
            value = self._file_storage.get_stored_path(value)
        extension = value.split(".")[-1]
        if self._extensions and extension not in self._extensions:
            raise ValueError(
                f"extension not supported, required extension in {self._extensions}",
            )
        return value

    def to_python_value(self, value: str) -> str | None:
        if not value or value.startswith("http"):
            return value
        try:
            is_success, url_or_error = self._file_storage.get_full_path(
                value,
                self._expire,
            )
        except Exception as e:
            raise ValueError(
                f"Obtain file from storage {self._file_storage} failed with exception {e}",
            ) from e
        else:
            if is_success:
                return url_or_error  # type: ignore
            raise ValueError(url_or_error)


class TimestampField(fields.DatetimeField):
    """
    Big integer for datetime field. (64-bit signed)
    """

    read_only: bool

    SQL_TYPE = "BIGINT"

    class _db_mysql:
        SQL_TYPE = "BIGINT"

    class _db_postgres:
        SQL_TYPE = "BIGINT"

    class _db_mssql:
        SQL_TYPE = "BIGINT"

    class _db_oracle:
        SQL_TYPE = "INT"

    def __init__(
        self,
        null: bool = True,
        default: str | None = None,
        read_only: bool = True,
        index: bool = False,
        description: str | None = None,
        validators: list[validators.Validator | Callable] | None = None,
    ) -> None:
        super().__init__(
            null=null,
            default=default,
            description=description,
            index=index,
            validators=validators,
        )
        self.read_only = read_only

    def to_db_value(self, value: int | datetime.datetime, instance: "TimestampField") -> str:  # type: ignore
        if value is None:
            return "0"
        if isinstance(value, datetime.datetime):
            value = int(value.timestamp())
        self.validate(value)
        return str(value)

    @property
    def constraints(self) -> dict:
        return {"readOnly": self.read_only}

    def to_python_value(
        self,
        value: str | int | None,
    ) -> datetime.datetime | None:
        if value is None or value in [0, "0"]:
            return None
        # if value == "0":
        #     # 区分 0 和 null
        #     return 0  # type: ignore
        from burnish_sdk_py.load_config import local_configs

        return datetime.datetime.fromtimestamp(
            value,  # type: ignore
            local_configs.RELATIONAL.zone,
        )


# class UUIDToBinaryField(fields.UUIDField):
#     """uuid 顺序主键, 使用uuid1(支持的并发足够)
#     将时间戳和变体号交换, 使其单向递增, 提升索引性能. 仅对uuid1有效
#     """

#     def __init__(self, pk: bool = False, **kwargs) -> None:
#         if pk and "default" not in kwargs:
#             kwargs["default"] = uuid.uuid1
#         super().__init__(pk=pk, **kwargs)

#     def to_db_value(  # type: ignore
#         self,
#         value: uuid.UUID | str | bytes | None,
#         instance: "type[models.Model] | models.Model",
#     ) -> bytes | None:
#         if value is None:
#             return None
#         # if isinstance(value, str):
#         # value = uuid.UUID(value)
#         from pypika import Query, Table, Field, Parameter, FormatParameter

#         match value:
#             case str():
#                 value = uuid.UUID(value)
#             case bytes():
#                 value = uuid.UUID(bytes=value)

#         return uuid_to_bin(value)
#         # return RawSQL(f'uuid_to_bin("{str(value)}", 1)')
#         # return f"uuid_to_bin(\"{str(value)}\", 1)"

#     def to_python_value(self, value: bytes | None) -> uuid.UUID | None:
#         if value is None:
#             return None
#         return bin_to_uuid(bytes=value)


class TimeField(fields.TimeField):
    def timedelta_to_time(self, td: datetime.timedelta) -> datetime.time:
        # 确保 timedelta 表示的总秒数不超过一天的秒数
        total_seconds = int(td.total_seconds()) % (24 * 3600)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        # 创建并返回一个 datetime.time 对象
        return datetime.time(hour=hours, minute=minutes, second=seconds)

    def to_python_value(
        self,
        value: Any,
    ) -> datetime.time | None:  # ruff: noqa: ANN401
        if isinstance(value, datetime.timedelta):
            value = self.timedelta_to_time(value)
        if value is not None:
            if isinstance(value, str):
                value = datetime.time.fromisoformat(value)
            if timezone.is_naive(value):
                value = value.replace(tzinfo=get_default_timezone())
        self.validate(value)
        return value  # type: ignore

    def to_db_value(
        self,
        value: datetime.time | None,  # type: ignore
        instance: "type[Model] | Model",
    ) -> datetime.time | datetime.timedelta | None:
        # Only do this if it is a Model instance, not class. Test for guaranteed instance var
        if hasattr(instance, "_saved_in_db") and (
            self.auto_now
            or (
                self.auto_now_add
                and getattr(instance, self.model_field_name) is None
            )
        ):
            now = timezone.now().time()
            setattr(instance, self.model_field_name, now)
            return now
        if value is not None and get_use_tz() and timezone.is_naive(value):
            warnings.warn(  # ruff: noqa: B028
                "TimeField {} received a naive time ({})"
                " while time zone support is active.".format(
                    self.model_field_name,
                    value,
                ),
                RuntimeWarning,
            )
            value = value.replace(tzinfo=get_default_timezone())
        self.validate(value)
        return value
