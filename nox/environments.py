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

__lazy_modules__ = {f"{__spec__.parent}._decorators", "functools"}

import functools
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, overload

from ._decorators import Func

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ._typing import Python

    RawFunc = Callable[..., Any]

__all__ = [
    "Environment",
    "RegistryData",
    "alias",
    "env",
    "get_registry_data",
    "register_env",
    "register_session_pair",
    "register_task",
    "reset_registry",
    "validate_name",
]


def __dir__() -> list[str]:
    return __all__


def validate_name(name: str, kind: str = "An environment") -> None:
    """Reject names that would break ``env:task`` identifiers."""
    if not name:
        msg = f"{kind} name cannot be empty."
        raise ValueError(msg)
    for char in ":()":
        if char in name:
            msg = f"{kind} name cannot contain {char!r}: {name!r}"
            raise ValueError(msg)


class Environment:
    """A declarative environment (virtualenv + how to provision it).

    Tasks are attached with the :meth:`task` decorator and run inside this
    environment, sharing a single virtualenv. Instantiating an ``Environment``
    registers it globally; subclasses can customize provisioning.
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
        # True for environments implicitly created by @nox.session; drives
        # the legacy naming/envdir behavior.
        self._session_compat = False

        if register:
            register_env(self)

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
        requires: Sequence[str] | None = None,
    ) -> Func | Callable[[RawFunc | Func], Func]:
        """Designate the decorated function as a task in this environment.

        Works with and without parentheses, like ``@nox.session``.
        """
        if func is None:
            return functools.partial(
                self.task, name=name, tags=tags, default=default, requires=requires
            )

        if isinstance(func, Func):
            func = func.func

        task_name = name or func.__name__
        validate_name(task_name, "A task")

        fn = Func(
            func,
            # Interpreter/venv settings are environment-level; they are filled
            # in from the (expanded) environment when the manifest is built.
            name=f"{self.name}:{task_name}",
            tags=tags,
            default=default,
            requires=requires,
        )
        fn.task_name = task_name
        fn.env = self

        register_task(self, task_name, fn)
        return fn


class _EnvAPI:
    """The ``nox.env`` callable namespace.

    Calling it creates a plain declarative :class:`Environment`; specialized
    environment types (lock file support, etc.) hang off it as attributes.
    """

    def __call__(self, name: str, /, **kwargs: Any) -> Environment:
        return Environment(name, **kwargs)


env = _EnvAPI()


class RegistryData(NamedTuple):
    """The full contents of the session registry."""

    envs: dict[str, Environment]
    tasks: dict[str, dict[str, Func]]
    aliases: dict[str, tuple[str, ...]]


_ENVS: dict[str, Environment] = {}
_TASKS: dict[str, dict[str, Func]] = {}
_ALIASES: dict[str, tuple[str, ...]] = {}


def reset_registry() -> None:
    _ENVS.clear()
    _TASKS.clear()
    _ALIASES.clear()


def _check_global_name(name: str, kind: str) -> None:
    if name in _ENVS:
        what = "session" if _ENVS[name]._session_compat else "environment"
        msg = f"A {what} named {name!r} is already registered; cannot register {kind} {name!r}."
        raise ValueError(msg)
    if name in _ALIASES:
        msg = f"An alias named {name!r} is already registered; cannot register {kind} {name!r}."
        raise ValueError(msg)


def register_env(environment: Environment) -> None:
    """Register an environment in the global registry."""
    validate_name(environment.name)
    _check_global_name(environment.name, "environment")
    _ENVS[environment.name] = environment
    _TASKS.setdefault(environment.name, {})


def register_task(environment: Environment, task_name: str, fn: Func) -> None:
    """Register a task under its environment."""
    if environment.name not in _ENVS:
        msg = f"The environment {environment.name!r} is not registered."
        raise ValueError(msg)
    tasks = _TASKS[environment.name]
    if task_name in tasks:
        msg = (
            f"The task {task_name!r} is already registered in "
            f"environment {environment.name!r}."
        )
        raise ValueError(msg)
    tasks[task_name] = fn


def register_session_pair(environment: Environment, fn: Func) -> None:
    """Register a classic session: an environment/task pair sharing a name.

    The name is not validated, since classic session names predate the
    ``env:task`` grammar; ``@nox.session`` warns about conflicting names.
    """
    environment._session_compat = True
    _ENVS[environment.name] = environment
    _TASKS[environment.name] = {environment.name: fn}
    fn.task_name = environment.name
    fn.env = environment


def alias(name: str, /, *targets: str) -> None:
    """Register a global alias that expands to one or more sessions.

    Args:
        name: The alias name; shares a namespace with environments.
        targets: One or more session identifiers (e.g. ``"tooling:lint"``).
    """
    validate_name(name, "An alias")
    if not targets:
        msg = f"Alias {name!r} needs at least one target."
        raise ValueError(msg)
    _check_global_name(name, "alias")
    _ALIASES[name] = targets


def get_registry_data() -> RegistryData:
    """Return a shallow copy of the full registry."""
    return RegistryData(
        envs=dict(_ENVS),
        tasks={name: dict(tasks) for name, tasks in _TASKS.items()},
        aliases=dict(_ALIASES),
    )
