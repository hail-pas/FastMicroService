from aerich import Command

from conf.config import local_configs
from conf.defines import VersionFilePath, ConnectionNameEnum
from common.fastapi import ServiceApi
from services.userCenter.factory import user_center_api


class RootApi(ServiceApi):
    async def before_server_start(self) -> None:
        for connection_name in ConnectionNameEnum:
            command = Command(
                tortoise_config=self.settings.relational.tortoise_orm_config,
                app=connection_name.value,
                location=VersionFilePath,
            )
            await command.init()
            await command.upgrade(run_in_transaction=True)


service_api = RootApi(code="ServiceRoot", settings=local_configs)

service_api.mount(
    "/user",
    user_center_api,
    "用户中心",
)
