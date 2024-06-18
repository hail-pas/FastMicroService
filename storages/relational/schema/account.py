from tortoise.contrib.pydantic import pydantic_model_creator

from storages.relational.models.account import Account


class AccountList(
    pydantic_model_creator(  # type: ignore
        Account,
        name="AccountList",
    ),
):
    ...


class AccountCreate(
    pydantic_model_creator(  # type: ignore
        Account,
        name="AccountCreate",
        exclude_readonly=True,
    ),
):
    ...
