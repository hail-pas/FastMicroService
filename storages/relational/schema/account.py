from datetime import datetime

from pydantic import ConfigDict
from tortoise.contrib.pydantic import pydantic_model_creator

from common.utils import DATETIME_FORMAT_STRING
from storages.relational.models.account import Account, Company


class CompanySimple(
    pydantic_model_creator(  # type: ignore
        Company,
        name="CompanySimple",
        model_config=ConfigDict(json_encoders={datetime: lambda v: v.strftime(DATETIME_FORMAT_STRING)}),
    ),
):
    ...


class AccountList(
    pydantic_model_creator(  # type: ignore
        Account,
        name="AccountList",
        # include=("id", "name", "created_at", "updated_at"),
        model_config=ConfigDict(json_encoders={datetime: lambda v: v.strftime(DATETIME_FORMAT_STRING)}),
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
