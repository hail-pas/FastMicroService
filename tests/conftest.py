import os
import sys
from pathlib import Path

from tests.factory.account import AccountFactory

# from tests.factory.company import CompanyFactory
# from tests.factory.role import RoleFactory

BASE_DIR = Path(__file__).parent.parent
os.environ.setdefault("BASE_DIR", str(BASE_DIR.absolute()))
sys.path.insert(0, "./service")

import asyncio
from types import ModuleType
from typing import Union
from contextlib import suppress
from urllib.parse import quote
from collections.abc import Iterable

import pytest
import pytest_asyncio
from httpx import AsyncClient
from tortoise import Tortoise
from conf.config import local_configs
from services.user_center.factory import user_center_api
from tortoise.exceptions import OperationalError, DBConnectionError
from tortoise.contrib.test import _generate_config
from storages.relational.models import Role, System, Account, Company

TORTOISE_TEST_DB = "sqlite://:memory:"

TEST_CONNECTION_CONGIF = local_configs.RELATIONAL.tortoise_orm_config.get(
    "connections",
).get("test")
if TEST_CONNECTION_CONGIF:
    TORTOISE_TEST_DB = f"mysql://{quote(TEST_CONNECTION_CONGIF.get('credentials').get('user'))}:{quote(TEST_CONNECTION_CONGIF.get('credentials').get('password'))}@{TEST_CONNECTION_CONGIF.get('credentials').get('host')}:{TEST_CONNECTION_CONGIF.get('credentials').get('port')}/{TEST_CONNECTION_CONGIF.get('db')}?charset=utf8mb4"  # noqa

BASE_URL = f"{local_configs.SERVER.REQUEST_SCHEME}://127.0.0.1:{local_configs.SERVER.PORT}"


def getTestDBConfig(
    app_label: str,
    modules: Iterable[Union[str, ModuleType]],
) -> dict:
    return _generate_config(
        TORTOISE_TEST_DB,
        app_modules={app_label: modules},
        testing=True,
        connection_label="default",
    )


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncClient:
    """不携带授权头部的 FastApi Client."""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def _initialize_db(request) -> None:
    """初始化数据库."""
    # db_url = "sqlite://:memory:"
    # initializer(["storages.relational.models"], db_url=db_url, app_label="master")
    # request.addfinalizer(finalizer)
    config = getTestDBConfig(
        app_label="master",
        modules=["storages.relational.models"],
    )

    async def _init_db() -> None:
        await Tortoise.init(config)
        with suppress(DBConnectionError, OperationalError):
            await Tortoise._drop_databases()

        await Tortoise.init(config, _create_db=True)
        await Tortoise.generate_schemas(safe=False)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_init_db())

    AsyncRedisUtil.init()

    def clean():
        loop.run_until_complete(Tortoise._drop_databases())
        loop.run_until_complete(AsyncRedisUtil.close())

    request.addfinalizer(clean)


@pytest_asyncio.fixture(scope="session")
async def initialize_system(_initialize_db) -> System:
    return await System.create(
        **{
            "code": "UserCenter",
            "label": "用户中心",
            "scenes": ["General"],
            "status": "enable",
        }
    )


@pytest_asyncio.fixture(scope="session")
async def initialize_super_admin_account(initialize_system: System) -> Account:
    """初始化resources、systems、roles、permissions、accounts
    做为测试的调用账户.
    """
    # 创建用户
    company = await Company.create(
        name="Burnish",
        address="xxxx",
    )

    await company.systems.add(initialize_system)

    super_admin = AccountFactory.extra_create(company, is_staff=True, is_super_admin=True)

    await super_admin.save()

    await super_admin.systems.add(initialize_system)

    # role = await Role.create(label="admin", code="admin")
    # await test_account.roles.add(role)
    return super_admin


@pytest_asyncio.fixture(scope="session")
async def get_super_admin_token(client: AsyncClient, initialize_super_admin_account: Account) -> str:
    account = initialize_super_admin_account
    username = account.username

    login_response = await client.post(
        url=f"/v1/auth/login",
        json={
            "username": username,
            "password": "JustForTest",
            "scene": "General",
        },
    )
    assert login_response.json().get("code") == 0

    return login_response.json().get("data").get("access_token")


@pytest_asyncio.fixture(scope="session")
async def authorized_super_admin_client(
    get_super_admin_token: str,
) -> AsyncClient:
    """带授权头部的 FastApi Client."""
    token = get_super_admin_token
    async with AsyncClient(
        app=app,
        base_url=BASE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            # "X-Role-Id": str(role.id),
        },
    ) as client:
        yield client
