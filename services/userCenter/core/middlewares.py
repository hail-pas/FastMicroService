from conf.config import local_configs
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.cors import CORSMiddleware
from burnish_sdk_py.middlewares import context, operation_record
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from common.middlewares.operation_record import (
    opeartion_flag_getter,
    operation_record_sinker,
)

roster = [
    # >>>>> Middleware Func
    context.contex_middleware,
    [GZipMiddleware, {"minimum_size": 1000}],
    operation_record.operation_record_middleware_wrapper(
        opeartion_flag_getter,
        operation_record_sinker,
    ),
    # >>>>> Middleware Class
    [
        CORSMiddleware,
        {
            "allow_origins": local_configs.SERVER.CORS.ALLOW_ORIGIN,
            "allow_credentials": local_configs.SERVER.CORS.ALLOW_CREDENTIAL,
            "allow_methods": local_configs.SERVER.CORS.ALLOW_METHODS,
            "allow_headers": local_configs.SERVER.CORS.ALLOW_HEADERS,
            "expose_headers": local_configs.SERVER.CORS.EXPOSE_HEADERS,
        },
    ],
    [
        TrustedHostMiddleware,
        {
            "allowed_hosts": local_configs.SERVER.ALLOW_HOSTS,
        },
    ],
]
