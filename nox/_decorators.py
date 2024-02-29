# Copyright 2020 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
import functools
import inspect
import types
from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

from . import _typing

if TYPE_CHECKING:
    from ._parametrize import Param

T = TypeVar("T", bound=Callable[..., Any])


class FunctionDecorator:
    """This is a function decorator."""

    def __new__(
        cls: Any, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> FunctionDecorator:
        obj = super().__new__(cls)
        functools.update_wrapper(obj, func)
        return cast(FunctionDecorator, obj)


def _copy_func(src: T, name: str | None = None) -> T:
    """This function copies another function, optionally with a new name."""

    dst = types.FunctionType(
        src.__code__,
        src.__globals__,
        name=name or src.__name__,
        argdefs=src.__defaults__,
        closure=src.__closure__,
    )
    dst.__dict__.update(copy.deepcopy(src.__dict__))
    dst = functools.update_wrapper(dst, src)
    dst.__kwdefaults__ = src.__kwdefaults__
    return cast(T, dst)


class Func(FunctionDecorator):
    """This is a function decorator that adds additional Nox-specific metadata."""

    def __init__(
        self,
        func: Callable[..., Any],
        python: _typing.Python = None,
        reuse_venv: bool | None = None,
        name: _typing.StrPath | None = None,
        venv_backend: Any = None,
        venv_params: Any = None,
        venv_location: _typing.StrPath | None = None,
        should_warn: Mapping[str, Any] | None = None,
        tags: Sequence[str] | None = None,
    ) -> None:
        self.func = func
        self.python = python
        self.reuse_venv = reuse_venv
        self.name = name
        self.venv_backend = venv_backend
        self.venv_params = venv_params
        self.venv_location = venv_location
        self.should_warn = dict(should_warn or {})
        self.tags = list(tags or [])

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)

    def copy(self, name: str | None = None) -> Func:
        """Copy this function with a new name."""

        return Func(
            _copy_func(self.func, name),
            self.python,
            self.reuse_venv,
            name,
            self.venv_backend,
            self.venv_params,
            self.venv_location,
            self.should_warn,
            self.tags,
        )


class Call(Func):
    """This represents a call of a function with a particular set of arguments."""

    def __init__(self, func: Func, param_spec: Param) -> None:
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
            func.venv_location,
            func.should_warn,
            func.tags,
        )
        self.call_spec = call_spec
        self.session_signature = session_signature

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.update(self.call_spec)
        return super().__call__(*args, **kwargs)

    @classmethod
    def generate_calls(
        cls: type[Call], func: Func, param_specs: Iterable[Param]
    ) -> list[Call]:
        """Generates a list of calls based on the function and parameters."""

        return [cls(func, param_spec) for param_spec in param_specs]
