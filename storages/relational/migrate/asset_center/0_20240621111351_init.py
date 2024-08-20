from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `vehiclebrand` (
    `id` BINARY(16) NOT NULL  PRIMARY KEY COMMENT '主键',
    `created_at` DATETIME(6) NOT NULL  COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL  COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `deleted_at` BIGINT   COMMENT '删除时间',
    `vehicle_brand` VARCHAR(16) NOT NULL  COMMENT '品牌',
    UNIQUE KEY `uid_vehiclebran_vehicle_61cdb8` (`vehicle_brand`, `deleted_at`),
    KEY `idx_vehiclebran_created_5e9375` (`created_at`),
    KEY `idx_vehiclebran_deleted_77212d` (`deleted_at`)
) CHARACTER SET utf8mb4 COMMENT='品牌';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
