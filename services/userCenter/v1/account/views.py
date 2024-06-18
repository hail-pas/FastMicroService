from fastapi import Request

from common.schemas import Pager
from common.responses import Resp, PageData
from services.dependencies import FixedContentQueryChecker
from services.userCenter.v1.account import router
from storages.relational.models.account import Account
from storages.relational.schema.account import AccountList, AccountCreate

checker = FixedContentQueryChecker("bar")


@router.post("/test")
async def create_account(request: Request, schema: AccountCreate) -> Resp[AccountList]:
    acc = await Account.create(**schema.model_dump())
    return Resp(data=AccountList.from_tortoise_orm(acc))


@router.get("/test")
async def get_account(request: Request) -> Resp[PageData[AccountList]]:
    acc = await AccountList.from_queryset(Account.all().prefetch_related("company"))
    return Resp(data=PageData(records=acc, total_count=100, pager=Pager(limit=10, offset=1)))
