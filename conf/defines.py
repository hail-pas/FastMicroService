import os
import enum
import multiprocessing
from typing import Self
from pathlib import Path
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager
from urllib.parse import unquote
from collections.abc import AsyncGenerator

from pydantic import HttpUrl, MySQLDsn, RedisDsn, BaseModel, ConfigDict, model_validator
from redis.retry import Retry
from redis.asyncio import Redis, ConnectionPool
from redis.backoff import NoBackoff


class EnvironmentEnum(str, enum.Enum):
    development = "development"
    test = "test"
    production = "production"


ENVIRONMENT = os.environ.get(
    "environment",  # noqa
    EnvironmentEnum.development.value,
)

BASE_DIR = Path(__file__).resolve().parent.parent


class ConnectionNameEnum(str, enum.Enum):
    """数据库连接名称"""

    default = "default"  # "默认连接"
    user_center = "user_center"  # "用户中心连接"
    asset_center = "asset_center"  # "资产中心连接"


VersionFilePath: str = f"{BASE_DIR}/storages/relational/migrate/"


class Relational(BaseModel):
    user_center: MySQLDsn
    asset_center: MySQLDsn

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo("Asia/Shanghai")

    @property
    def tortoise_orm_config(self) -> dict:
        echo = True
        return {
            "connections": {
                ConnectionNameEnum.user_center.value: {
                    "engine": "tortoise.backends.mysql",
                    "credentials": {
                        "host": self.user_center.host,
                        "port": self.user_center.port,
                        "user": self.user_center.username,
                        "password": unquote(self.user_center.password) if self.user_center.password else "",
                        "database": self.user_center.path.strip("/"),  # type: ignore
                        "echo": echo,
                        "maxsize": 10,
                    },
                },
                ConnectionNameEnum.asset_center.value: {
                    "engine": "tortoise.backends.mysql",
                    "credentials": {
                        "host": self.asset_center.host,
                        "port": self.asset_center.port,
                        "user": self.asset_center.username,
                        "password": unquote(self.asset_center.password) if self.asset_center.password else "",
                        "database": self.asset_center.path.strip("/"),  # type: ignore
                        "echo": echo,
                        "maxsize": 10,
                    },
                },
            },
            "apps": {
                ConnectionNameEnum.user_center.value: {
                    "models": [
                        "aerich.models",
                        "storages.relational.models.account",
                    ],
                    "default_connection": ConnectionNameEnum.user_center.value,
                },
                ConnectionNameEnum.asset_center.value: {
                    "models": [
                        "storages.relational.models.vehicle",
                    ],
                    "default_connection": ConnectionNameEnum.asset_center.value,
                },
            },
            # "use_tz": True,   # Will Always Use UTC as Default Timezone
            "timezone": "Asia/Shanghai",
            # 'routers': ['path.router1', 'path.router2'],
        }


class RedisConfig(BaseModel):
    user_center: RedisDsn
    asset_center: RedisDsn
    max_connections: int = 10

    def connection_pool(self, service: ConnectionNameEnum) -> ConnectionPool:
        return ConnectionPool.from_url(
            url=getattr(self, service.value),
            max_connections=self.max_connections,
            decode_responses=True,
            encoding_errors="strict",
            retry=Retry(NoBackoff(), retries=5),
            health_check_interval=30,
        )

    @asynccontextmanager
    async def get_redis(self, service: ConnectionNameEnum, **kwargs) -> AsyncGenerator[Redis, None]:  # type: ignore
        try:
            r: Redis = Redis(
                connection_pool=self.connection_pool(service),
                **kwargs,
            )
            yield r
        finally:
            await r.close()


class CorsConfig(BaseModel):
    allow_origins: list[str] = ["*"]
    allow_credentials: bool = True
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    expose_headers: list[str] = []

    @property
    def headers(self) -> dict:
        result = {
            "Access-Control-Allow-Origin": ",".join(self.allow_origins) if "*" not in self.allow_origins else "*",
            "Access-Control-Allow-Credentials": str(
                self.allow_credentials,
            ).lower(),
            "Access-Control-Expose-Headers": ",".join(self.allow_headers) if "*" not in self.allow_headers else "*",
            "Access-Control-Allow-Methods": ",".join(self.allow_methods) if "*" not in self.allow_methods else "*",
        }
        if self.expose_headers:
            result["Access-Control-Expose-Headers"] = ", ".join(
                self.expose_headers,
            )

        return result


class ProfilingConfig(BaseModel):
    secret: str
    interval: float = 0.001


class ServiceStringConfig(BaseModel):
    user_center: str
    asset_center: str


class Server(BaseModel):
    address: HttpUrl = HttpUrl("http://0.0.0.0:8000")
    cors: CorsConfig = CorsConfig()
    worker_number: int = multiprocessing.cpu_count() * int(os.getenv("WORKERS_PER_CORE", "2")) + 1
    profiling: ProfilingConfig | None = None
    allow_hosts: list = ["*"]
    static_path: str = "/static"
    docs_uri: str = "/docs"
    redoc_uri: str = "/redoc"
    openapi_uri: str = "/openapi.json"

    redirect_openapi_prefix: ServiceStringConfig = ServiceStringConfig(
        user_center="/user",
        asset_center="/asset",
    )


class Project(BaseModel):
    unique_code: ServiceStringConfig = ServiceStringConfig(
        user_center="UserCenter",
        asset_center="AssetCenter",
    )
    name: str = "FastService"
    description: str = "FastService"
    debug: bool = False
    environment: EnvironmentEnum = EnvironmentEnum.production
    log_dir: str = "logs/"
    sentry_dsn: HttpUrl | None = None

    class SwaggerServerConfig(BaseModel):
        url: HttpUrl
        description: str

    swagger_servers: list[SwaggerServerConfig] = []

    @model_validator(mode="after")
    def check_debug_options(self) -> Self:
        assert not (
            self.debug and self.environment == EnvironmentEnum.production
        ), "Production cannot set with debug enabled"
        return self

    @property
    def base_dir(self) -> Path:
        return BASE_DIR
