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


main_swagger_servers = [s.model_dump() for s in local_configs.project.swagger_servers]
user_center_swagger_servers = []
alert_center_swagger_servers = []
for s in local_configs.project.swagger_servers:
    u_s = s.model_copy()
    u_s.url = f"{s.url}user"
    user_center_swagger_servers.append(u_s.model_dump())
    a_s = s.model_copy()
    a_s.url = f"{s.url}alert"
    alert_center_swagger_servers.append(a_s.model_dump())

user_center_api.servers = user_center_swagger_servers


service_api = RootApi(
    code="ServiceRoot",
    settings=local_configs,
    title="主服务",
    description="主服务",
    version="1.0.0",
    servers=main_swagger_servers,
)
service_api.mount(
    "/user",
    user_center_api,
    "用户中心",
)
