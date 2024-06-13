from pathlib import Path

from common.types import StrEnumMore
from conf.defines import (
    ENVIRONMENT,
    BASE_DIR,
    CONFIG_FILE_EXTENSION,
    Oss,
    Redis,
    Project,
    Relational,
    BaseLocalConfig,
    UserCenterRedis,
    create_local_configs,
)
from pydantic import BaseModel

class ConnectionNameEnum(StrEnumMore):
    """数据库连接名称"""

    default = ("default", "默认连接")
    user_center = ("user_center", "用户中心连接")
    asset_center = ("asset_center", "资产中心连接")


class ApplicationRelational(BaseModel):
    UserCenter: Relational
    AssetCenter: Relational

    VersionFilePath: str = f"{BASE_DIR}/storages/relational/migrate/versions/"

    @property
    def tortoise_orm_config(self) -> dict:
        echo = False
        return {
            "connections": {
                ConnectionNameEnum.user_center.value: {
                    "engine": "tortoise.backends.mysql",
                    "credentials": {
                        "host": self.UserCenter.HOST,
                        "port": self.UserCenter.PORT,
                        "user": self.UserCenter.USERNAME,
                        "password": self.UserCenter.PASSWORD,
                        "database": self.UserCenter.DB,
                        "echo": echo,
                        "maxsize": 10,
                    },
                },
                ConnectionNameEnum.asset_center.value: {
                    "engine": "tortoise.backends.mysql",
                    "credentials": {
                        "host": self.AssetCenter.HOST,
                        "port": self.AssetCenter.PORT,
                        "user": self.AssetCenter.USERNAME,
                        "password": self.AssetCenter.PASSWORD,
                        "database": self.AssetCenter.DB,
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
                        "aerich.models",
                        "storages.relational.models.vehicle",
                    ],
                    "default_connection": ConnectionNameEnum.asset_center.value,
                },

            },
            # "use_tz": True,   # Will Always Use UTC as Default Timezone
            "timezone": "Asia/Shanghai",
        }


class ApplicationRedis(BaseModel):
    """应用Redis配置"""
    UserCenter: UserCenterRedis
    AssetCenter: Redis


class ApplicationOss(BaseModel):
    """应用OSS配置"""
    UserCenter: Oss
    AssetCenter: Oss



class ApplicationProject(BaseModel):
    """应用项目配置"""
    UserCenter: Project
    AssetCenter: Project



class LocalConfig(BaseLocalConfig):
    # PROJECT: ApplicationProject

    # SERVER: Server

    # PROFILING: ProfilingConfig

    RELATIONAL: ApplicationRelational

    REDIS: ApplicationRedis

    # AES_SECRET: str

    # SIGN_SECRET: str

    # OSS: ApplicationOss


config_path: Path = Path(
    f"{str(BASE_DIR)}/etc/{ENVIRONMENT.lower()}.{CONFIG_FILE_EXTENSION}",
)

local_configs: LocalConfig = create_local_configs(LocalConfig, config_path)  # type: ignore
