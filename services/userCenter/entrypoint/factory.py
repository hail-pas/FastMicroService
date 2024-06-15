from conf.config import local_configs
from common.fastapi import ServiceApi
from services.userCenter.routers.account.views import router as account_router

user_center_api = ServiceApi(code="userCenter", settings=local_configs)

user_center_api.amount_app_or_router(roster=[(account_router, "/account", "用户管理")])
