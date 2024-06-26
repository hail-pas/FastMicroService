from tortoise.contrib.pydantic import pydantic_model_creator

from common.pydantic import CommonConfigDict, optional
from storages.relational.models.account import Account, Company


class CompanySimple(
    pydantic_model_creator(  # type: ignore
        Company,
        name="CompanySimple",
        model_config=CommonConfigDict,
    ),
):
    ...


class AccountList(
    pydantic_model_creator(  # type: ignore
        Account,
        name="AccountList",
        # include=("id", "name", "created_at", "updated_at"),
        model_config=CommonConfigDict,
    ),
):
    company: CompanySimple


class AccountCreate(
    pydantic_model_creator(  # type: ignore
        Account,
        name="AccountCreate",
        exclude_readonly=True,
    ),
):
    ...


@optional()
class AccountUpdate(AccountCreate):
    ...
