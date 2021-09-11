import copy
import functools
import inspect
import types
from typing import Any, Callable, Dict, Iterable, List, Optional, cast

from . import _typing

if _typing.TYPE_CHECKING:
    from ._parametrize import Param


class FunctionDecorator:
    def __new__(
        cls, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> "FunctionDecorator":
        obj = super().__new__(cls)
        return cast("FunctionDecorator", functools.wraps(func)(obj))


def _copy_func(src: Callable, name: Optional[str] = None) -> Callable:
    dst = types.FunctionType(
        src.__code__,
        src.__globals__,  # type: ignore
        name=name or src.__name__,
        argdefs=src.__defaults__,  # type: ignore
        closure=src.__closure__,  # type: ignore
    )
    dst.__dict__.update(copy.deepcopy(src.__dict__))
    dst = functools.update_wrapper(dst, src)
    dst.__kwdefaults__ = src.__kwdefaults__  # type: ignore
    return dst


class Func(FunctionDecorator):
    def __init__(
        self,
        func: Callable,
        python: _typing.Python = None,
        reuse_venv: Optional[bool] = None,
        name: Optional[str] = None,
        venv_backend: Any = None,
        venv_params: Any = None,
        should_warn: Optional[Dict[str, Any]] = None,
    ):
        self.func = func
        self.python = python
        self.reuse_venv = reuse_venv
        self.venv_backend = venv_backend
        self.venv_params = venv_params
        self.should_warn = should_warn or dict()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)

    def copy(self, name: Optional[str] = None) -> "Func":
        return Func(
            _copy_func(self.func, name),
            self.python,
            self.reuse_venv,
            name,
            self.venv_backend,
            self.venv_params,
            self.should_warn,
        )


class Call(Func):
    def __init__(self, func: Func, param_spec: "Param") -> None:
        call_spec = param_spec.call_spec
        session_signature = f"({param_spec})"

        # Determine the Python interpreter for the session using either @session
        # or @parametrize. For backwards compatibility, we only use a "python"
        # parameter in @parametrize if the session function does not expect it
        # as a normal argument, and if the @session decorator does not already
        # specify `python`.

        python = func.python
        if python is None and "python" in call_spec:
            signature = inspect.signature(func.func)
            if "python" not in signature.parameters:
                python = call_spec.pop("python")

        super().__init__(
            func,
            python,
            func.reuse_venv,
            None,
            func.venv_backend,
            func.venv_params,
            func.should_warn,
        )
        self.call_spec = call_spec
        self.session_signature = session_signature

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.update(self.call_spec)
        return super().__call__(*args, **kwargs)

    @classmethod
    def generate_calls(cls, func: Func, param_specs: "Iterable[Param]") -> "List[Call]":
        return [cls(func, param_spec) for param_spec in param_specs]
