import sys
import threading
from typing import Generic, TypeVar, ParamSpec
from functools import wraps
from collections.abc import Callable

P = ParamSpec("P")
T = TypeVar("T")


class SingletonClassMeta(type, Generic[T]):
    _instances: dict[type[T], T] = {}

    def __call__(cls: type[T], *args, **kwargs) -> T:
        if cls not in cls._instances:  # type: ignore
            cls._instances[cls] = super().__call__(*args, **kwargs)  # type: ignore
        return cls._instances[cls]  # type: ignore


def timelimit(
    timeout: int | float,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """A decorator to limit a function to `timeout` seconds, raising `TimeoutError`
    if it takes longer.
        >>> import time
        >>> def meaningoflife():
        ...     time.sleep(.2)
        ...     return 42
        >>>
        >>> timelimit(.1)(meaningoflife)()
        Traceback (most recent call last):
            ...
        RuntimeError: took too long
        >>> timelimit(1)(meaningoflife)()
        42
    _Caveat:_ The function isn't stopped after `timeout` seconds but continues
    executing in a separate thread. (There seems to be no way to kill a thread.)
    inspired by <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473878>.
    """

    def _1(function: Callable[P, T]) -> Callable[P, T | None]:
        @wraps(function)
        def _2(*args: P.args, **kw: P.kwargs) -> T | None:
            class Dispatch(threading.Thread):
                def __init__(self) -> None:
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None

                    self.setDaemon(True)
                    self.start()

                def run(self) -> None:
                    try:
                        self.result = function(*args, **kw)  # type: ignore
                    except Exception:
                        self.error = sys.exc_info()  # type: ignore

            c = Dispatch()
            c.join(timeout)
            if c.is_alive():
                raise RuntimeError("took too long")
            if c.error:
                raise c.error[1]  # type: ignore
            return c.result

        return _2

    return _1  # type: ignore
