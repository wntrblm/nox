# Copyright 2026 Alethea Katherine Flowers
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

__lazy_modules__ = {"functools", "nox.registry", f"{__spec__.parent}._decorators"}

import functools
from typing import TYPE_CHECKING, Any, Literal, overload

import nox.registry

from ._decorators import Func

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ._typing import Python

    RawFunc = Callable[..., Any]

__all__ = [
    "Environment",
    "env",
]


def __dir__() -> list[str]:
    return __all__


class Environment:
    """An environment (a virtualenv) that tasks run in.

    Tasks are attached with the :meth:`task` decorator and run inside this
    environment, sharing a single virtualenv. Instantiating an ``Environment``
    registers it globally. Available as ``nox.env.standard``.
    """

    def __init__(
        self,
        name: str,
        *,
        python: Python = None,
        venv_backend: str | None = None,
        venv_params: Sequence[str] = (),
        reuse_venv: bool | None = None,
        download_python: Literal["auto", "never", "always"] | None = None,
        tags: Sequence[str] | None = None,
        register: bool = True,
    ) -> None:
        self.name = name
        self.python = python
        self.venv_backend = venv_backend
        self.venv_params = venv_params
        self.reuse_venv = reuse_venv
        self.download_python = download_python
        self.tags = list(tags or [])

        if register:
            nox.registry.register_env(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

    @overload
    def task(self, func: RawFunc | Func, /) -> Func: ...

    @overload
    def task(
        self,
        func: None = ...,
        /,
        *,
        name: str | None = ...,
        tags: Sequence[str] | None = ...,
        default: bool = ...,
        explicit: bool = ...,
        requires: Sequence[str] | None = ...,
    ) -> Callable[[RawFunc | Func], Func]: ...

    def task(
        self,
        func: RawFunc | Func | None = None,
        /,
        *,
        name: str | None = None,
        tags: Sequence[str] | None = None,
        default: bool = True,
        explicit: bool = False,
        requires: Sequence[str] | None = None,
    ) -> Func | Callable[[RawFunc | Func], Func]:
        """Designate the decorated function as a task in this environment.

        Works with and without parentheses, like ``@nox.session``.

        ``default=False`` keeps the task out of a bare ``nox`` run.
        ``explicit=True`` keeps it out of environment selectors such as
        ``nox -s env`` or ``requires=["env"]``; it then only runs when named
        as ``env:task`` or through an alias.
        """
        if func is None:
            return functools.partial(
                self.task,
                name=name,
                tags=tags,
                default=default,
                explicit=explicit,
                requires=requires,
            )

        if isinstance(func, Func):
            func = func.func

        task_name = name or func.__name__
        nox.registry.validate_name(task_name, "A task")

        fn = Func(
            func,
            # Interpreter/venv settings are environment-level; they are filled
            # in from the (expanded) environment when the manifest is built.
            name=f"{self.name}:{task_name}",
            tags=tags,
            default=default,
            explicit=explicit,
            requires=requires,
        )
        fn.task_name = task_name
        fn.env = self

        nox.registry.register_task(self, task_name, fn)
        return fn


class _EnvAPI:
    """The ``nox.env`` namespace of environment types."""

    standard = Environment


env = _EnvAPI()
