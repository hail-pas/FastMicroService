from tortoise import fields

from conf.defines import ConnectionNameEnum
from common.tortoise.models.base import BaseModel


class VehicleBrand(BaseModel):
    vehicle_brand = fields.CharField(
        max_length=16,
        description="品牌",
    )

    class Meta:
        table_description = "品牌"
        ordering = ["-id"]
        unique_together = (("vehicle_brand", "deleted_at"),)
        app = ConnectionNameEnum.asset_center.value
