from aerich import Command

from conf.config import local_configs
from conf.defines import VersionFilePath, ConnectionNameEnum
from common.fastapi import ServiceApi
from services.user_center.factory import user_center_api


class RootApi(ServiceApi):
    async def before_server_start(self) -> None:
        for connection_name in ConnectionNameEnum:
            if connection_name.value == "default":
                continue
            command = Command(
                tortoise_config=self.settings.relational.tortoise_orm_config,
                app=connection_name.value,
                location=VersionFilePath,
            )
            await command.init()
            await command.upgrade(run_in_transaction=True)


description = """
==== 欢迎来到主服务 ====
<br><br>
User-Center: <a href="/user/docs/">用户中心服务接口文档</a>
<br><br>
Vehicle-Center: <a href="/vehicle/docs/">车辆中心服务接口文档</a>
<br><br>
"""

service_api = RootApi(
    code="ServiceRoot",
    settings=local_configs,
    title="主服务",
    description=description,
    version="1.0.0",
    servers=[s.model_dump() for s in local_configs.project.swagger_servers],
)
service_api.mount(
    "/user",
    user_center_api,
    "用户中心",
)
