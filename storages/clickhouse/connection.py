from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import httpx
from loguru import logger
from aiochclient import ChClient  # type: ignore

timeout = httpx.Timeout(5.0, connect=10.0)
limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)


@asynccontextmanager
async def get_clickhouse_client(url: str, username: str, password: str) -> AsyncGenerator[ChClient, None]:
    ch_client = None
    try:
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as http_client:
            ch_client = ChClient(http_client, url=url, user=username, password=password)
            yield ch_client
    except Exception as e:
        logger.error(f"Error connecting to Clickhouse: {e}")
        raise e
    finally:
        if ch_client:
            await ch_client.close()
