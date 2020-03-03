import functools
from typing import Any, Callable, cast


class FunctionDecorator:
    def __new__(
        cls, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> "FunctionDecorator":
        obj = super().__new__(cls)
        return cast("FunctionDecorator", functools.wraps(func)(obj))
