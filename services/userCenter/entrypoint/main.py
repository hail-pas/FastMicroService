import sys
from typing import Any

from common.fastapi import ServiceApi

sys.path.append(".")  # 将当前目录加入到环境变量中

import asyncio  # noqa

import gunicorn.app.base  # type:ignore
from aerich import Command  # type:ignore

from conf.config import local_configs  # noqa
from conf.defines import VersionFilePath, ConnectionNameEnum  # noqa

"""FastAPI"""


class FastApiApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app: ServiceApi, options: dict | None = None) -> None:
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self) -> None:
        config = {key: value for key, value in self.options.items() if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self) -> ServiceApi:
        return self.application


def post_fork(server: Any, worker: Any) -> None:  # ruff: noqa
    # Important: The import of skywalking should be inside the post_fork function
    # if local_configs.PROJECT.SKYWALKINGT_SERVER:
    #     print({"level": "INFO", "message": "Skywalking agent started"})
    #     import os

    #     from skywalking import agent, config

    #     # append pid-suffix to instance name
    #     # This must be done to distinguish instances if you give your instance customized names
    #     # (highly recommended to identify workers)
    #     # Notice the -child(pid) part is required to tell the difference of each worker.

    #     config.init(
    #         agent_collector_backend_services="192.168.3.46:11800",
    #         agent_name=f"python:{local_configs.PROJECT.NAME}",
    #         agent_instance_name=agent_instance_name,
    #         plugin_fastapi_collect_http_params=True,
    #         agent_protocol="grpc",
    #     )

    #     agent.start()
    pass


async def run_migrations() -> None:
    command = Command(
        tortoise_config=local_configs.relational.tortoise_orm_config,
        app=ConnectionNameEnum.user_center.value,
        location=VersionFilePath,
    )
    await command.init()
    await command.upgrade(run_in_transaction=True)


if __name__ == "__main__":
    # gunicorn core.factory:app
    # --workers 4
    # --worker-class uvicorn.workers.UvicornWorker
    # --timeout 180
    # --graceful-timeout 120
    # --max-requests 4096
    # --max-requests-jitter 512
    # --log-level debug
    # --logger-class core.loguru.GunicornLogger
    # --bind 0.0.0.0:80
    # import sys
    asyncio.get_event_loop().run_until_complete(run_migrations())
    options = {
        "bind": f"{local_configs.server.address.host}:{local_configs.server.address.port}",
        "workers": local_configs.server.worker_number,
        "worker_class": "uvicorn.workers.UvicornWorker",
        "debug": local_configs.project.debug,
        "log_level": "debug" if local_configs.project.debug else "info",
        "max_requests": 4096,  # # 最大请求数之后重启worker，防止内存泄漏
        "max_requests_jitter": 512,  # 随机重启防止所有worker一起重启：randint(0, max_requests_jitter)
        "graceful_timeout": 120,
        "timeout": 180,
        "logger_class": "common.log.GunicornLogger",
        # "config": "entrypoint.gunicorn_conf.py",
        # "post_fork": "entrypoint.main.post_fork",
    }

    from services.userCenter.entrypoint.factory import user_center_api

    FastApiApplication(user_center_api, options).run()
