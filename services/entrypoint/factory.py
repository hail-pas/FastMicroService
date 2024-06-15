from fastapi import FastAPI

from services.userCenter.entrypoint.factory import user_center_api

service_api = FastAPI(code="microService", settings=None)

service_api.mount(
    "/user",
    user_center_api,
    "用户中心",
)
