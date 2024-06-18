from aerich import Command

from conf.config import local_configs
from conf.defines import VersionFilePath, ConnectionNameEnum
from common.fastapi import ServiceApi
from services.exceptions import roster as exception_handler_roster
from services.middlewares import roster as middleware_roster
from services.userCenter.v1 import router as v1_router
from services.userCenter.v2 import router as v2_router


class UserCenterServiceApi(ServiceApi):
    async def before_server_start(self) -> None:
        command = Command(
            tortoise_config=self.settings.relational.tortoise_orm_config,
            app=ConnectionNameEnum.asset_center.value,
            location=VersionFilePath,
        )
        await command.init()
        await command.upgrade(run_in_transaction=True)


user_center_api = UserCenterServiceApi(code="UserCenter", settings=local_configs)

user_center_api.setup_middleware(roster=middleware_roster)
user_center_api.setup_exception_handlers(roster=exception_handler_roster)

user_center_api.amount_app_or_router(roster=[(v1_router, "", "v1")])
user_center_api.amount_app_or_router(roster=[(v2_router, "", "v2")])
