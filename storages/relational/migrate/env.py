from conf.config import local_configs

TORTOISE_ORM_CONFIG = local_configs.relational.tortoise_orm_config


# aerich init -t storages.relational.migrate.env.TORTOISE_ORM_CONFIG --location storages/relational/migrate/versions
# aerich --app {app} init-db
# aerich --app {app} migrate
