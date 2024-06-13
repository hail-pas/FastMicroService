import os
import enum
import multiprocessing
from typing import Any, Literal, Optional
from pathlib import Path
from zoneinfo import ZoneInfo
from functools import lru_cache

import orjson
import tomlkit
from pydantic import BaseModel, BaseSettings, validator, root_validator
from redis.retry import Retry
from redis.asyncio import ConnectionPool
from redis.backoff import NoBackoff
from pydantic.env_settings import SettingsSourceCallable


class EnvironmentEnum(str, enum.Enum):
    development = "Development"
    test = "Test"
    production = "Production"


ENVIRONMENT = os.environ.get(
    "environment",  # noqa
    EnvironmentEnum.development.value.capitalize(),
)

CONFIG_FILE_EXTENSION = "json"


BASE_DIR = Path(__file__).resolve().parent.parent


class HostAndPort(BaseModel):
    HOST: str
    PORT: int | None


class Relational(HostAndPort):
    USERNAME: str
    PASSWORD: str
    DB: str
    TYPE: Literal["postgresql", "mysql"] = "postgresql"
    TIMEZONE: str | None = "Asia/Shanghai"

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE or "Asia/Shanghai")

    @property
    def url(self) -> str:
        pkg = "asyncpg"
        if self.TYPE == "mysql":
            pkg = "aiomysql"
        return f"{self.TYPE}+{pkg}://{self.USERNAME}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"  # noqa


class Redis(HostAndPort):
    USERNAME: str | None = None
    PASSWORD: str | None = None
    DB: int = 0
    MAX_CONNECTIONS: int = 20


class UserCenterRedis(Redis):
    @property
    def connection_pool(self) -> ConnectionPool:
        return ConnectionPool(
            host=self.HOST,
            port=self.PORT,
            db=self.DB,
            username=self.USERNAME,
            password=self.PASSWORD,
            max_connections=self.MAX_CONNECTIONS,
            decode_responses=True,
            encoding_errors="strict",
            retry=Retry(NoBackoff(), retries=5),
            health_check_interval=30,
        )


class Oss(BaseModel):
    ACCESS_KEY_ID: str
    ACCESS_KEY_SECRET: str
    ENDPOINT: str
    EXTERNAL_ENDPOINT: str | None = None
    BUCKET_NAME: str
    CNAME: str | None = None  # 自定义域名绑定
    BUCKET_ACL_TYPE: str | None = "private"
    EXPIRE_TIME: int = 60
    MEDIA_LOCATION: str | None = None
    STATIC_LOCATION: str | None = None


class CorsConfig(BaseModel):
    ALLOW_ORIGIN: list[str] = ["*"]
    ALLOW_CREDENTIAL: bool = True
    ALLOW_METHODS: list[str] = ["*"]
    ALLOW_HEADERS: list[str] = ["*"]
    EXPOSE_HEADERS: list[str] = []

    @property
    def headers(self) -> dict:
        result = {
            "Access-Control-Allow-Origin": ",".join(self.ALLOW_ORIGIN)
            if "*" not in self.ALLOW_ORIGIN
            else "*",
            "Access-Control-Allow-Credentials": str(
                self.ALLOW_CREDENTIAL,
            ).lower(),
            "Access-Control-Expose-Headers": ",".join(self.ALLOW_HEADERS)
            if "*" not in self.ALLOW_HEADERS
            else "*",
            "Access-Control-Allow-Methods": ",".join(self.ALLOW_METHODS)
            if "*" not in self.ALLOW_METHODS
            else "*",
        }
        if self.EXPOSE_HEADERS:
            result["Access-Control-Expose-Headers"] = ", ".join(
                self.EXPOSE_HEADERS,
            )

        return result


class Server(HostAndPort):
    REQUEST_SCHEME: str = "https"
    CORS: CorsConfig = CorsConfig()
    WORKERS_NUM: int = (
        multiprocessing.cpu_count() * int(os.getenv("WORKERS_PER_CORE", "2"))
        + 1
    )
    ALLOW_HOSTS: list = ["*"]
    STATIC_PATH: str = "/static"
    STATIC_DIR: str = f"{str(BASE_DIR.absolute())}/static"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"
    REDIRECT_OPENAPI_URL_PREFIX: str = ""

class ProfilingConfig(BaseModel):
    SECRET: str
    INTERVAL: float = 0.001


class Project(BaseModel):
    UNIQUE_CODE: str  # 项目唯一标识，用于redis前缀
    NAME: str = "FastService"
    DESCRIPTION: str = "FastService"
    VERSION: str = "v1"
    DEBUG: bool = False
    ENVIRONMENT: str = EnvironmentEnum.production.value
    LOG_DIR: str = "logs/"
    SENTRY_DSN: str | None = None
    SWAGGER_SERVERS: list[dict] = []

    @root_validator
    def check_debug_options(cls, values: dict) -> dict:
        env_options = [e.value for e in EnvironmentEnum]
        env = values["ENVIRONMENT"]
        debug = values["DEBUG"]
        assert (
            env in env_options
        ), f'Illegal environment config value, options: {",".join(env_options)}'
        assert not (
            debug and env == EnvironmentEnum.production.value
        ), "Production cannot set with debug enabled"
        return values

    # @property
    # def BASE_DIR(self) -> Path:
    #     return BASE_DIR


class Hbase(BaseModel):
    SERVERS: list = []


class Kafka(BaseModel):
    SERVERS: list = []


class Jwt(BaseModel):
    SECRET: str
    # AUTH_HEADER_PREFIX: str = "JWT"
    ISSUER: str
    SCENE: list[str] = ["General"]
    EXPIRATION_DELTA_MINUTES: int = 432000
    REFRESH_EXPIRATION_DELTA_DELTA_MINUTES: int = 4320

    @validator("SECRET")
    def read_secret(cls, v: str) -> str:
        try:
            return Path(v).read_text()
        except Exception:
            return v


class BaseLocalConfig(BaseSettings):
    """全部的配置信息."""

    class Config:
        case_sensitive = True
        env_file_encoding = "utf-8"

@lru_cache
def create_local_configs(
    setting_cls: type[BaseSettings],
    config_file: Path,
) -> BaseSettings:
    """create json file base setting object"""

    class _Settings(setting_cls):  # type: ignore
        class Config(getattr(setting_cls, "Config", object)):  # type: ignore
            @classmethod
            def customise_sources(
                cls,
                init_settings: SettingsSourceCallable,
                env_settings: SettingsSourceCallable,
                file_secret_settings: SettingsSourceCallable,
            ) -> tuple[SettingsSourceCallable, ...]:
                def json_config_settings_source(
                    settings: BaseSettings,
                ) -> dict[str, Any]:
                    encoding = settings.__config__.env_file_encoding
                    return orjson.loads(  # type: ignore
                        config_file.read_text(encoding),
                    )

                return (
                    init_settings,
                    json_config_settings_source,
                    env_settings,
                    file_secret_settings,
                )

    return _Settings()
