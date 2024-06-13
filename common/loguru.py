# import ast
# import sys
# import logging
# import traceback
# from enum import Enum
# from types import FrameType
# from typing import Any, TextIO, cast
# from itertools import chain
# from collections.abc import Callable

# from loguru import logger
# from loguru import Message
# from gunicorn import glogging  # type: ignore
# from rich.console import Console

# from common.types import IntEnumMore
# from burnish_sdk_py.config import EnvironmentEnum
# from burnish_sdk_py.load_config import local_configs

# # from common.responses import ResponseCodeEnum
# from burnish_sdk_py.common.decorators import extend_enum

# # from starlette.concurrency import iterate_in_threadpool


# console = Console()

# LOG_LEVEL = logging.DEBUG if local_configs.PROJECT.DEBUG else logging.INFO


# class LogLevelEnum(IntEnumMore):
#     """日志级别"""

#     CRITICAL = (logging.CRITICAL, "CRITICAL")
#     # FATAL = ("50", "FATAL")
#     ERROR = (logging.ERROR, "ERROR")
#     # WARN = ("30", "WARN")
#     WARNING = (logging.WARNING, "WARNING")
#     INFO = (logging.INFO, "INFO")
#     DEBUG = (logging.DEBUG, "DEBUG")
#     NOTSET = (logging.NOTSET, "NOTSET")


# class ColorEnum(str, Enum):
#     # colorize log
#     blue = "\x1b[38;5;39m"
#     cyan = "\x1b[36m"
#     green = "\x1b[32;20m"
#     yellow = "\x1b[38;5;226m"
#     red = "\x1b[38;5;196m"
#     bold_red = "\x1b[31;1m"
#     # reset = "\x1b[0m"
#     no_color = "\033[0m"


# class ChangableLoggerName(str, Enum):
#     root = "root"
#     fastaapi = "fastapi"
#     tortoise = "tortoise"


# @extend_enum(ChangableLoggerName)  # type: ignore
# class LoggerNameEnum(str, Enum):
#     gunicorn_error = "gunicorn.error"
#     gunicorn_asgi = "gunicorn.asgi"
#     gunicorn_gunicorn = "gunicorn.access"
#     uvicorn_error = "uvicorn.error"
#     uvicorn_asgi = "uvicorn.asgi"
#     uvicorn_access = "uvicorn.access"


# DynamicLogLevelConfig: dict[LoggerNameEnum, LogLevelEnum] = {}

# IgonredLoggerNames = [
#     LoggerNameEnum.uvicorn_access.value,
# ]


# def to_int_level(level: str | int) -> int:
#     if level in LogLevelEnum.labels:  # type: ignore
#         return LogLevelEnum.values[LogLevelEnum.labels.index(level)]  # type: ignore
#     return int(level)


# class InterceptHandler(logging.Handler):
#     """Logs to loguru from Python logging module"""

#     def emit(self, record: logging.LogRecord) -> None:
#         if record.name in IgonredLoggerNames:
#             return
#         # 动态日志级别, 涉及到进程、线程间共享字典，性能损耗大
#         # if DynamicLogLevelConfig.get(name, to_int_level(LOG_LEVEL)) > to_int_level(log["level"]):
#         #         return
#         try:
#             level = logger.level(record.levelname).name
#         except ValueError:
#             level = str(record.levelno)

#         # 动态日志级别, 涉及到进程、线程间共享字典，性能损耗大
#         # name = record.name
#         # if DynamicLogLevelConfig.get(name, to_int_level(LOG_LEVEL)) > to_int_level(level):
#         #     return

#         # _logger = logger
#         # request_id =
#         # if request_id:
#         #     _logger = _logger.bind(request_id=request_id)

#         if record.exc_info:
#             # 异常日志处理
#             if local_configs.PROJECT.DEBUG:
#                 # print(
#                 #     f"{ColorEnum.bold_red.value}{traceback.format_exc()}{request_id}"
#                 # )
#                 # console.print_exception(traceback.format_exc(), log_locals=True)
#                 print(traceback.format_exc())
#             else:
#                 # 保持日志一致性
#                 tb = traceback.extract_tb(sys.exc_info()[2])
#                 # 获取最后一个堆栈帧的文件名和行号
#                 file_name, line_num, func_name, code_str = tb[-1]
#                 location = f"{file_name}:{func_name}:{line_num}"
#                 logger.bind(location=location).critical(
#                     traceback.format_exc(),
#                 )
#             return

#         frame, depth = logging.currentframe(), 2
#         while frame.f_code.co_filename == logging.__file__:  # noqa: WPS609
#             frame = cast(FrameType, frame.f_back)
#             depth += 1

#         logger.opt(depth=depth, exception=record.exc_info).log(
#             level,
#             record.getMessage(),
#         )


# def setup_loguru_logging_intercept(
#     level: int = logging.DEBUG,
#     modules: tuple = (),
# ) -> None:
#     logging.basicConfig(handlers=[InterceptHandler()], level=level)  # noqa
#     for logger_name in chain(("",), modules):
#         mod_logger = logging.getLogger(logger_name)
#         mod_logger.handlers = [InterceptHandler(level=level)]
#         mod_logger.setLevel(level)
#         # mod_logger.propagate = False


# def serialize(record: dict) -> dict:
#     """Serialize the JSON log."""
#     log = {}
#     name = record["name"]
#     log["level"] = record["level"].name
#     log["time"] = record["time"].strftime("%Y-%m-%d %H:%M:%S %Z %z")
#     log["message"] = record["message"]
#     if record["extra"].get("json"):
#         # logger.bind(json=True).info()
#         # dict/list or python object string convert
#         log["message"] = ast.literal_eval(log["message"])
#     location = name
#     log["name"] = location
#     if record["function"]:
#         location = f'{location}:{record["function"]}'
#     log["location"] = f'{location}:{record["line"]}'
#     log.update(record.get("extra", {}))
#     return log


# def json_sink(message: Message) -> None:  # from loguru import Message
#     serialized = serialize(message.record)  # type: ignore
#     if not serialized:
#         return

#     # color = ""
#     # if local_configs.PROJECT.ENVIRONMENT == EnvironmentEnum.development.value:
#     #     level_color = {
#     #         "TRACE": ColorEnum.blue.value,
#     #         "DEBUG": ColorEnum.cyan.value,
#     #         "INFO": ColorEnum.green.value,
#     #         "SUCCESS": ColorEnum.no_color.value,
#     #         "WARNING": ColorEnum.yellow.value,
#     #         "ERROR": ColorEnum.red.value,
#     #         "CRITICAL": ColorEnum.bold_red.value,
#     #     }
#     #     color = level_color.get(serialized["level"], ColorEnum.no_color.value)
#     # print(f"{color}{serialized}")
#     if EnvironmentEnum.development.value == local_configs.PROJECT.ENVIRONMENT:
#         console.print_json(data=serialized)
#     else:
#         print(serialized)


# class GunicornLogger(glogging.Logger):
#     def __init__(self, cfg: Any) -> None:  # ruff: noqa: ANN401
#         super().__init__(cfg)
#         LOGGING_MODULES = (
#             LoggerNameEnum.gunicorn_error.value,
#             LoggerNameEnum.gunicorn_asgi.value,
#             LoggerNameEnum.gunicorn_gunicorn.value,
#         )
#         setup_loguru_logging_intercept(
#             level=logging.getLevelName(LOG_LEVEL),
#             modules=LOGGING_MODULES,
#         )


# def init_loguru(
#     sink: TextIO | Callable[[Message], None] | logging.Handler = json_sink,
# ) -> None:
#     # loguru
#     logger.remove()
#     # logger.add(
#     #     sink=os.path.join(
#     #         BASE_DIR,
#     #         f'{local_configs.PROJECT.LOG_DIR}{datetime_now().strftime("%Y-%m-%d")}'
#     #          '-{local_configs.PROJECT.UNIQUE_CODE}-service.log',
#     #     ),
#     #     rotation="500 MB",  # 日志文件最大限制500mb
#     #     retention="30 days",  # 最长保留30天
#     #     format="{message}",  # 日志显示格式
#     #     compression="zip",  # 压缩形式保存
#     #     encoding="utf-8",  # 编码
#     #     level=LOG_LEVEL,  # 日志级别
#     #     enqueue=True,  # 默认是线程安全的，enqueue=True使得多进程安全
#     #     serialize=True,
#     #     backtrace=True,
#     #     diagnose=True,
#     # )
#     logger.add(
#         sink=sink,  # type: ignore
#         format="{message}",  # 日志显示格式
#         level=LOG_LEVEL,  # 日志级别
#         enqueue=True,  # 默认是线程安全的，enqueue=True使得多进程安全
#         serialize=True,
#         backtrace=True,
#         diagnose=True,
#         colorize=True,
#     )

#     UVICORN_LOGGING_MODULES = (
#         LoggerNameEnum.root.value,  # type: ignore
#         LoggerNameEnum.uvicorn_error.value,
#         LoggerNameEnum.uvicorn_asgi.value,
#         LoggerNameEnum.uvicorn_access.value,
#         LoggerNameEnum.fastaapi.value,  # type: ignore
#     )

#     setup_loguru_logging_intercept(
#         level=logging.getLevelName(LOG_LEVEL),
#         modules=UVICORN_LOGGING_MODULES,
#     )

#     # Tortoise
#     setup_loguru_logging_intercept(
#         level=logging.getLevelName(logging.INFO),
#         modules=[
#             LoggerNameEnum.tortoise.value,  # type: ignore
#         ],
#     )

#     # # Uvicorn access log gunicorn启动时不生效
#     # setup_loguru_logging_intercept(
#     #     level=logging.getLevelName(logging.ERROR), modules=[LoggerNameEnum.uvicorn_access.value,]
#     # )

#     # disable duplicate logging
#     logging.getLogger(LoggerNameEnum.root.value).handlers.clear()  # type: ignore
#     logging.getLogger("uvicorn").handlers.clear()
#     logging.captureWarnings(True)
