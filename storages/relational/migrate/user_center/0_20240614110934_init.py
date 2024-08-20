from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `company` (
    `id` BINARY(16) NOT NULL  PRIMARY KEY COMMENT '主键',
    `created_at` DATETIME(6) NOT NULL  COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL  COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `deleted_at` BIGINT   COMMENT '删除时间',
    `name` VARCHAR(50) NOT NULL  COMMENT '企业名称',
    `industry` VARCHAR(50)   COMMENT '企业所属行业',
    KEY `idx_company_created_976855` (`created_at`),
    KEY `idx_company_deleted_fd6a3f` (`deleted_at`)
) CHARACTER SET utf8mb4 COMMENT='企业';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
