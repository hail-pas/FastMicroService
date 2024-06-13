from tortoise import Tortoise

from conf.defines import ConnectionNameEnum

Tortoise.init_models(
    [
        "storages.relational.models.account",
    ],
    ConnectionNameEnum.user_center.value,
)

Tortoise.init_models(
    [
        "storages.relational.models.vehicle",
    ],
    ConnectionNameEnum.asset_center.value,
)
