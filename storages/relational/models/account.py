from tortoise import fields

from conf.defines import ConnectionNameEnum
from common.tortoise.models.base import BaseModel


class Company(BaseModel):
    """企业"""

    name = fields.CharField(
        max_length=50,
        description="企业名称",
    )
    industry = fields.CharField(max_length=50, null=True, description="企业所属行业")

    class Meta:
        table_description = "企业"
        ordering = ["-id"]
        app = ConnectionNameEnum.user_center.value
        # using = ConnectionNameEnum.user_center.value


class Account(BaseModel):
    """账户"""

    company: fields.ForeignKeyRelation[Company] = fields.ForeignKeyField(
        f"{ConnectionNameEnum.user_center.value}.Company",
        related_name="accounts",
        description="所属企业",
    )
    name = fields.CharField(max_length=50, description="账户名称")

    class Meta:
        table_description = "账户"
        ordering = ["-id"]
