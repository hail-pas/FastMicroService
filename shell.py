import pdb  # noqa
import cProfile
import importlib

from IPython import start_ipython
from traitlets.config import Config
from conf.config import local_configs
from tortoise import Tortoise

async def init_ctx_relational() -> None:

    await Tortoise.init(config=local_configs.relational.tortoise_orm_config)


# async def init_ctx_redis() -> None:

    # AsyncRedisUtil.init()


async def init_ctx() -> None:

    await init_ctx_relational()
    # await init_ctx_redis()


if __name__ == "__main__":

    # models = {cls.__name__: cls for cls in BaseModel.__subclasses__()}
    main = importlib.import_module("__main__")
    ctx = main.__dict__
    ctx.update(
        {
            # **models,
            "ipdb": pdb,
            "cProfile": cProfile,
        },
    )
    conf = Config()
    conf.InteractiveShellApp.exec_lines = [
        "print('System Ready!')",
        "from shell import init_ctx",
        "await init_ctx()",
    ]
    # DEBUG=10, INFO=20, WARN=30
    conf.InteractiveShellApp.log_level = 30
    conf.TerminalInteractiveShell.loop_runner = "asyncio"
    conf.TerminalInteractiveShell.colors = "neutral"
    conf.TerminalInteractiveShell.autoawait = True
    start_ipython(argv=[], user_ns=ctx, config=conf)

