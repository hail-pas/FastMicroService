from typing import Any
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from loguru import logger
from fastapi import Depends, FastAPI
from tortoise import Tortoise
from conf.config import LocalConfig, local_configs

# from fastapi_cache import FastAPICache
from burnish_sdk_py.redis import AsyncRedisUtil
from common.constant.tags import TagsEnum
from burnish_sdk_py.dependencies import global_request_header_required
from burnish_sdk_py.common.loguru import init_loguru

# from fastapi_cache.backends.redis import RedisBackend
from burnish_sdk_py.common.fastapi import (
    RespSchemaAPIRouter,
    amount_apps,
    setup_sentry,
    setup_middleware,
    setup_static_app,
)
from burnish_sdk_py.common.responses import AesResponse
from burnish_sdk_py.common.exceptions import setup_exception_handlers

init_loguru()


class MainApp(FastAPI):
    plugins: dict[str, Any] = {}

    @property
    def settings(self) -> LocalConfig:
        return local_configs


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # 初始化及退出清理
    # redis
    AsyncRedisUtil.init()

    # tortoise
    await Tortoise.init(config=local_configs.RELATIONAL.tortoise_orm_config)

    yield

    await Tortoise.close_connections()
    # await FastAPICache.clear()
    await AsyncRedisUtil.close()


def create_app(current_settings: LocalConfig) -> FastAPI:
    main_app = MainApp(
        # debug=current_settings.PROJECT.DEBUG,
        title=current_settings.PROJECT.NAME,
        description=current_settings.PROJECT.DESCRIPTION,
        default_response_class=AesResponse,
        openapi_url=current_settings.SERVER.OPENAPI_URL,
        docs_url=current_settings.SERVER.DOCS_URL if current_settings.PROJECT.DEBUG else None,
        redoc_url=current_settings.SERVER.REDOC_URL,
        version=current_settings.PROJECT.VERSION,
        lifespan=lifespan,
        openapi_tags=[{"name": name, "description": description} for name, description in TagsEnum.choices],
        swagger_ui_parameters={
            "url": f"{local_configs.SERVER.REDIRECT_OPENAPI_URL_PREFIX}/openapi.json",
            "persistAuthorization": bool(current_settings.PROJECT.DEBUG),
        },
        dependencies=[
            Depends(global_request_header_required),
        ],
    )
    main_app.router.route_class = RespSchemaAPIRouter
    main_app.logger = logger.bind(name=current_settings.PROJECT.UNIQUE_CODE)  # type: ignore
    main_app.servers = [
        {
            "url": f"http://127.0.0.1:{local_configs.SERVER.PORT}",
            "description": "Local environment",
        },
    ] + local_configs.PROJECT.SWAGGER_SERVERS or []
    # thread local just flask like g
    # main_app.add_middleware(GlobalsMiddleware)
    # 挂载apps下的路由 以及 静态资源路由
    from apis.urls import roster as app_roster

    amount_apps(main_app, app_roster)
    setup_static_app(main_app)
    # 初始化全局 middleware
    from core.middlewares import roster as middleware_roster

    setup_middleware(main_app, middleware_roster)
    # 初始化全局 error handling
    from burnish_sdk_py.common.exceptions import roster as excep_roster

    setup_exception_handlers(main_app, excep_roster)
    # 初始化 sentry
    if local_configs.PROJECT.SENTRY_DSN:
        setup_sentry(current_settings)

    return main_app


logger.bind(json=True).info(
    {**local_configs.PROJECT.dict(), **local_configs.SERVER.dict()},
)
app = create_app(current_settings=local_configs)
