import uuid
from typing import Annotated

from fastapi import Query, Request

from services.crud import (
    update,
    get_all,
    create_obj,
    pagination_factory,
    obj_prefetch_fields,
)
from common.schemas import CRUDPager
from common.responses import Resp, PageData
from services.user_center.v1.account import router
from storages.relational.models.account import Account
from storages.relational.schema.account import AccountList, AccountCreate, AccountUpdate
from services.user_center.v1.account.schema import AccountFilterSchema


@router.post(
    path="",
    summary="Create a new account",
    description="Create a new account",
)
async def create_account(request: Request, schema: AccountCreate) -> Resp[AccountList]:
    acc = await create_obj(Account, schema.model_dump(exclude_unset=True))
    acc = await obj_prefetch_fields(acc, AccountList)
    return Resp(data=AccountList.model_validate(acc))


@router.get(
    path="",
    summary="Get all accounts",
    description="Get all accounts",
)
async def get_account(
    request: Request,
    filter_schema: Annotated[AccountFilterSchema, Query()],  # type: ignore
    pager: CRUDPager = pagination_factory(
        Account,
        {
            "name",
        },
        {
            "created_at",
        },
        AccountList,
        1000,
    ),
) -> Resp[PageData[AccountList]]:
    return await get_all(Account.all(), pager, **filter_schema.model_dump(exclude_unset=True, exclude_none=True))


@router.patch(
    path="/{account_id}",
    summary="Update an account",
    description="Update an account",
)
async def update_account(request: Request, account_id: uuid.UUID, schema: AccountUpdate) -> Resp[AccountList]:
    return await update(
        queryset=Account.all(),
        id=account_id,
        data=schema.model_dump(exclude_unset=True),
        pydantic_model_type=AccountList,
    )
