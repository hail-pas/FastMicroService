from fastapi import Request

from common.responses import Resp
from services.dependencies import FixedContentQueryChecker
from storages.relational.models.account import Account
from storages.relational.schema.account import AccountList, AccountCreate
from services.userCenter.routers.v1.account import router

checker = FixedContentQueryChecker("bar")


@router.post("/test")
async def create_account(request: Request, schema: AccountCreate) -> Resp[AccountList]:
    acc = await Account.create(**schema.model_dump())
    return Resp(data=AccountList.from_tortoise_orm(acc))
