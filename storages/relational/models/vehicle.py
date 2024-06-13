from tortoise import fields
from common.tortoise.models.base import (
    BaseModel,
)

from conf.config import ConnectionNameEnum


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


class VehicleSeries(BaseModel):
    vehicle_brand = fields.CharField(
        max_length=16,  # type: ignore
        description="品牌",
    )
    vehicle_series = fields.CharField(
        max_length=16,
        description="车系",
    )
    remark = fields.CharField(
        max_length=128,
        description="备注",
        null=True,
    )

    class Meta:
        table_description = "车系"
        ordering = ["-id"]
        unique_together = (("vehicle_brand", "vehicle_series", "deleted_at"),)
        app = ConnectionNameEnum.asset_center.value
