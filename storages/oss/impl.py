from conf.config import local_configs
from common.utils import normalize_url
from conf.defines import EnvironmentEnum
from common.oss.file import OssFile
from common.tortoise import StorageMixin
from common.decorators import SingletonClassMeta


class XxxOss(
    OssFile,
    StorageMixin,
    metaclass=SingletonClassMeta["XxxOss"],  # type: ignore
):
    def __init__(
        self,
        app_id: str = local_configs.third.xoss.app_id,
        app_secret: str = local_configs.third.xoss.app_secret,
        endpoint: str = local_configs.third.xoss.endpoint,
        base_path: str = local_configs.third.xoss.base_path,
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.endpoint = normalize_url(endpoint)
        self.base_path = base_path
        self.verify_ssl = local_configs.project.environment not in [
            EnvironmentEnum.development,
            EnvironmentEnum.local,
        ]
