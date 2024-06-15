from loguru import logger
from pyinstrument import Profiler
from fastapi.responses import HTMLResponse
from starlette_context import request_cycle_context
from starlette.requests import Request, HTTPConnection
from starlette.responses import Response
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette_context.plugins.base import Plugin

from conf.config import local_configs
from common.context import (
    RequestIdPlugin,
    RequestProcessInfoPlugin,
    RequestStartTimestampPlugin,
)
from common.decorators import SingletonClassMeta


async def contex_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    class ContextMiddleware(metaclass=SingletonClassMeta):
        plugins: list[Plugin]

        def __init__(self, plugins: list[Plugin]) -> None:
            self.plugins = plugins

        async def set_context(
            self,
            request: Request | HTTPConnection,
        ) -> dict:
            return {plugin.key: await plugin.process_request(request) for plugin in self.plugins}

        async def enrich_response(self, response: Response) -> None:
            for i in self.plugins:
                await i.enrich_response(response)

        async def __call__(
            self,
            request: Request,
            call_next: RequestResponseEndpoint,
        ) -> Response:
            context = await self.set_context(request)
            with request_cycle_context(context), logger.contextualize(
                request_id=context.get(RequestIdPlugin.key),
            ):
                profile_secret = request.query_params.get("profile_secret", "")
                if (
                    profile_secret
                    and local_configs.server.profiling
                    and profile_secret == local_configs.server.profiling.secret
                ):
                    profiler = Profiler(
                        interval=local_configs.server.profiling.interval,
                        async_mode="enabled",
                    )
                    profiler.start()
                    await call_next(request)
                    profiler.stop()
                    return HTMLResponse(profiler.output_html())
                response = await call_next(request)
                await self.enrich_response(response)
                return response

    _context_middleware = ContextMiddleware(
        plugins=[
            RequestStartTimestampPlugin(),
            RequestIdPlugin(),
            RequestProcessInfoPlugin(),
        ],
    )

    return await _context_middleware(request, call_next)


roster = [
    # >>>>> Middleware Func
    contex_middleware,
    (GZipMiddleware, {"minimum_size": 1000}),
    # >>>>> Middleware Class
    (
        CORSMiddleware,
        {
            "allow_origins": local_configs.server.cors.allow_origins,
            "allow_credentials": local_configs.server.cors.allow_credentials,
            "allow_methods": local_configs.server.cors.allow_methods,
            "allow_headers": local_configs.server.cors.allow_headers,
            "expose_headers": local_configs.server.cors.expose_headers,
        },
    ),
    (
        TrustedHostMiddleware,
        {
            "allowed_hosts": local_configs.server.allow_hosts,
        },
    ),
]
