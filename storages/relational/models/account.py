from tortoise import fields, models

from conf.config import ConnectionNameEnum
from common.regex import EMAIL_REGEX
from common.utils import get_enum_field_display
from common.tortoise.validators import RegexValidator
from common.tortoise.models.base import NotDeletedManager


class Company(models.Model):
    """企业"""

    name = fields.CharField(
        max_length=50,
        description="企业名称",
    )
    legal_representative_email = fields.CharField(
        max_length=100,
        null=True,
        description="法人邮箱",
        help_text="长度不超过100个字符",
        validators=[
            RegexValidator(
                EMAIL_REGEX.pattern,
                0,
                default_ctx={"field_name": "法人邮箱"},
            ),
        ],
    )
    landline_area_code = fields.CharField(
        max_length=4,
        null=True,
        description="企业座机区号",
        help_text="长度不超过4个字符",
    )
    landline_number = fields.CharField(
        max_length=8,
        null=True,
        description="企业座机号",
        help_text="长度不超过8个字符",
    )
    type = fields.CharField(max_length=50, null=True, description="企业类型")
    industry = fields.CharField(max_length=50, null=True, description="企业所属行业")

    def status_display(self) -> str:
        """状态显示"""
        return get_enum_field_display(self, "status")  # type: ignore

    class PydanticMeta:
        computed = ("status_display",)
        backward_relations = False

    class Meta:
        table_description = "企业"
        ordering = ["-id"]
        manager = NotDeletedManager()
        app = ConnectionNameEnum.user_center.value
