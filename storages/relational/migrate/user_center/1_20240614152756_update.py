from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `account` (
    `id` BINARY(16) NOT NULL  PRIMARY KEY COMMENT '主键',
    `created_at` DATETIME(6) NOT NULL  COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL  COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `deleted_at` BIGINT   COMMENT '删除时间',
    `name` VARCHAR(50) NOT NULL  COMMENT '账户名称',
    `company_id` BINARY(16) NOT NULL COMMENT '所属企业',
    CONSTRAINT `fk_account_company_4619ac14` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`) ON DELETE CASCADE,
    KEY `idx_account_created_028865` (`created_at`),
    KEY `idx_account_deleted_c0aa6b` (`deleted_at`)
) CHARACTER SET utf8mb4 COMMENT='账户';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `account`;"""
