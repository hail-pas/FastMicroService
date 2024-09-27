import random
from typing import Generic, TypeVar
from collections import defaultdict
from collections.abc import Iterable, AsyncGenerator

import six  # type: ignore
from pydantic import Field, BaseModel
from thbase.config import ClientConfig, ProtocolType, TransportType  # type: ignore
from thbase.thrift2.client import Client  # type: ignore
from thbase.thrift2.operation import Get, Scan, _column_format  # type: ignore

from conf.config import local_configs
from common.pydantic import create_sub_fields_model


def get_random_host_and_port(servers: list[str]) -> tuple[str, str]:
    if not servers:
        raise RuntimeError
    thrift_server = servers[random.randint(0, len(servers) - 1)]
    return thrift_server.split(":")  # type: ignore


def bytes_increment(b: bytes) -> bytes | None:
    """Increment and truncate a byte string (for sorting purposes)

    This functions returns the shortest string that sorts after the given
    string when compared using regular string comparison semantics.

    This function increments the last byte that is smaller than ``0xFF``, and
    drops everything after it. If the string only contains ``0xFF`` bytes,
    `None` is returned.
    """
    assert isinstance(b, six.binary_type)
    b = bytearray(b)  # Used subset of its API is the same on Python 2 and 3.
    for i in range(len(b) - 1, -1, -1):
        if b[i] != 0xFF:
            b[i] += 1
            return bytes(b[: i + 1])
    return None


def get_thrift2_client(
    servers: list[str] = local_configs.hbase.servers,
) -> Client:
    host, port = get_random_host_and_port(servers)
    conf = ClientConfig(
        thrift_host=host,
        port=int(port),
        retry_times=3,
        retry_timeout=10,
        connection_retry_times=3,
        connection_retry_timeout=10,
        transport_type=TransportType.BUFFERED,
        protocol_type=ProtocolType.BINARY,
        use_ssl=False,
        batch_size=10,
        use_http=False,
    )
    client = Client(conf)
    client.open_connection()
    return client


DataT = TypeVar("DataT", bound=BaseModel)


class HBaseORM(BaseModel, Generic[DataT]):
    """thrift2"""

    row_key: str = Field(description="主键", alias="row_key")

    @classmethod
    def get_fields_from_columns(cls, columns: Iterable[bytes]) -> set[str]:
        field_names = {
            "row_key",
        }
        for field_name, mf in cls.model_fields.items():  # ModelField
            if mf.alias.encode() in columns:
                field_names.add(field_name)
        return field_names

    @classmethod
    def get_columns_from_fields(cls, fields: set[str]) -> set[bytes] | None:
        columns = set()
        for mf in cls.model_fields.values():  # ModelField
            if mf.alias in fields and "display" not in mf.alias:
                columns.add(mf.alias.encode())
        return columns or None

    # @classmethod
    # async def get_row(  # type: ignore
    #     cls,
    #     row_key: str,
    #     columns: Iterable[bytes] | None = None,
    #     timestamp: int | None = None,
    #     include_timestamp: bool = False,
    # ) -> DataT | None:
    #     specify_cls = cls
    #     if columns:
    #         specify_cls = create_sub_fields_model(  # type: ignore
    #             cls,
    #             cls.get_fields_from_columns(columns),
    #         )
    #     else:
    #         columns = [
    #             mf.alias.encode()
    #             for mf in cls.__fields__.values()
    #             if mf.alias != "row_key"
    #         ]
    #     exc: Exception | None = None
    #     for _ in range(cls.Meta.retry_times):
    #         try:
    #             async with cls.Meta.pool.connection() as conn:
    #                 table: Table = conn.table(cls.Meta.table)  # type: ignore
    #                 data = await table.row(
    #                     row_key.encode(),
    #                     columns,
    #                     timestamp,
    #                     include_timestamp,
    #                 )
    #                 if not data:
    #                     return None
    #                 data = {k.decode(): v for k, v in data.items()}
    #             return specify_cls(**data, row_key=row_key)  # type: ignore
    #         except Exception as exc:
    #             exc = exc
    #     if exc:  # type: ignore
    #         raise exc  # type: ignore

    # async def put_row(
    #     self,
    #     row_key: str,
    #     timestamp: int | None = None,
    #     wal: bool = True,
    # ) -> None:
    #     exc: Exception | None = None
    #     for _ in range(self.Meta.retry_times):
    #         try:
    #             async with self.Meta.pool.connection() as conn:
    #                 table: Table = conn.table(self.Meta.table)  # type: ignore
    #                 await table.put(
    #                     row_key.encode(),
    #                     {
    #                         k.encode(): v.encode()  # type: ignore
    #                         for k, v in self.dict(by_alias=True).items()
    #                     },
    #                     timestamp,
    #                     wal,
    #                 )
    #                 return
    #         except Exception as exc:
    #             exc = exc
    #     if exc:  # type: ignore
    #         raise exc  # type: ignore

    # @classmethod
    # async def delete_row(
    #     cls,
    #     row_key: str,
    #     columns: Iterable[bytes] | None = None,
    #     timestamp: int | None = None,
    #     wal: bool = True,
    # ) -> None:
    #     exc: Exception | None = None
    #     for _ in range(cls.Meta.retry_times):
    #         try:
    #             async with cls.Meta.pool.connection() as conn:
    #                 table: Table = conn.table(cls.Meta.table)  # type: ignore
    #                 await table.delete(
    #                     row_key.encode(),
    #                     columns,
    #                     timestamp,
    #                     wal,
    #                 )
    #                 return
    #         except Exception as exc:
    #             exc = exc
    #     if exc:  # type: ignore
    #         raise exc  # type: ignore

    @classmethod
    async def scan(
        cls,
        row_start: bytes | None = None,
        row_stop: bytes | None = None,
        row_prefix: bytes | None = None,
        columns: Iterable[bytes] | None = None,
        filter_: bytes | None = None,  # noqa
        # timestamp: int | None = None,
        # include_timestamp: bool = False,
        batch_size: int = 2000,
        # scan_batching: int | None = None,
        limit: int | None = None,
        # sorted_columns: bool = False,
        reverse: bool = False,
    ) -> AsyncGenerator[DataT, None]:
        specify_cls = cls
        if columns:
            specify_cls = create_sub_fields_model(  # type: ignore
                cls,
                cls.get_fields_from_columns(columns),
            )
        else:
            columns = [
                mf.alias.encode()
                for mf in cls.model_fields.values()
                if mf.alias != "row_key" and "display" not in mf.alias
            ]
        if row_prefix is not None:
            if row_start is not None or row_stop is not None:
                raise TypeError(
                    "'row_prefix' cannot be combined with 'row_start' or 'row_stop'",
                )

            if reverse:
                row_start = bytes_increment(row_prefix)
                row_stop = row_prefix
            else:
                row_start = row_prefix
                row_stop = bytes_increment(row_prefix)

        t_scan = Scan(
            start_row=row_start,
            stop_row=row_stop,
            num_rows=limit,
            # family=list(columns)[0].decode().split(":")[0],
            # qualifier=[i.decode().split(":")[1] for i in columns],
            reversed=reverse,
            filter_bytes=filter_,
        )
        qualifiers = defaultdict(list)
        for i in columns:
            family, qualifier = i.decode().split(":")
            qualifiers[family].append(qualifier)
        columns = []
        for k, v in qualifiers.items():
            columns += _column_format(k, v)
        t_scan.core.batchSize = batch_size
        t_scan.core.limit = limit
        t_scan.core.columns = columns
        exc: Exception | None = None
        for _ in range(cls.Meta.retry_times):
            try:
                client = get_thrift2_client()
                results = client._scan(
                    table_name=cls.Meta.table.encode(),
                    scan=t_scan,
                )
                client.close_connection()
                if not results or len(results) == 0:
                    return
                for i in results:
                    if not i.row:  # type: ignore
                        continue
                    temp = {}
                    for cv in iter(i.columnValues):  # type: ignore
                        key = f"{cv.family.decode()}:{cv.qualifier.decode()}"
                        temp[key] = cv.value
                    yield specify_cls(row_key=i.row, **temp)  # type: ignore
                return
            except Exception as e:
                exc = e
        if exc:
            raise exc

    @classmethod
    async def get_row_list(
        cls,
        row_key_list: list[str],
        columns: Iterable[bytes] | None = None,
        timestamp: int | None = None,
        include_timestamp: bool = False,
    ) -> AsyncGenerator[DataT, None]:
        specify_cls = cls
        if columns:
            specify_cls = create_sub_fields_model(  # type: ignore
                cls,
                cls.get_fields_from_columns(columns),
            )
        else:
            columns = [mf.alias.encode() for mf in cls.model_fields.values() if mf.alias != "row_key"]
        exc: Exception | None = None

        # batch get operation
        get_list = []
        for row_key in row_key_list:
            get_list.append(Get(row=row_key, family=None, qualifier=None, max_versions=1))
        # res = client._get_rows(table_name=table_name, gets=get_list)
        for _ in range(cls.Meta.retry_times):
            try:
                client = get_thrift2_client()
                results = client._get_rows(table_name=cls.Meta.table.encode(), gets=get_list)
                client.close_connection()
            except Exception as e:
                exc = e

        if exc:  # type: ignore
            raise exc  # type: ignore

        if not results or len(results) == 0:
            return

        for i in results:
            if not i.row:  # type: ignore
                continue
            temp = {}
            for cv in iter(i.columnValues):  # type: ignore
                key = f"{cv.family.decode()}:{cv.qualifier.decode()}"
                temp[key] = cv.value
            yield specify_cls(row_key=i.row, **temp)  # type: ignore
        return

    class Meta:
        # abstract = True
        retry_times = 7
        table: str
