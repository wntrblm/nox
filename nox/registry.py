# Copyright 2017 Alethea Katherine Flowers
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

__lazy_modules__ = {"functools", "warnings", f"{__spec__.parent}._decorators"}

import functools
import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, overload

from ._decorators import Func

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ._typing import Python
    from .environments import Environment

__all__ = [
    "RegistryData",
    "alias",
    "get",
    "get_registry",
    "register_env",
    "register_task",
    "reset",
    "session_decorator",
    "validate_name",
]


def __dir__() -> list[str]:
    return __all__


RawFunc = Callable[..., Any]


class RegistryData(NamedTuple):
    """The full contents of the registry."""

    #: Classic sessions and environments by name, in registration order.
    entries: dict[str, Func | Environment]
    #: The tasks of each environment.
    tasks: dict[str, dict[str, Func]]
    aliases: dict[str, tuple[str, ...]]


_REGISTRY: dict[str, Func | Environment] = {}
_TASKS: dict[str, dict[str, Func]] = {}
_ALIASES: dict[str, tuple[str, ...]] = {}


def reset() -> None:
    _REGISTRY.clear()
    _TASKS.clear()
    _ALIASES.clear()


def get() -> dict[str, Func]:
    """Return a shallow copy of the registered sessions.

    Only includes classic sessions, for backward compatibility. Use
    :func:`get_registry` for the full registry.
    """
    return {name: fn for name, fn in _REGISTRY.items() if isinstance(fn, Func)}


def get_registry() -> RegistryData:
    """Return a shallow copy of the full registry."""
    return RegistryData(
        entries=dict(_REGISTRY),
        tasks={name: dict(tasks) for name, tasks in _TASKS.items()},
        aliases=dict(_ALIASES),
    )


def validate_name(name: str, kind: str = "An environment") -> None:
    """Reject names that would break ``env:task`` identifiers."""
    if not name:
        msg = f"{kind} name cannot be empty."
        raise ValueError(msg)
    for char in ":()":
        if char in name:
            msg = f"{kind} name cannot contain {char!r}: {name!r}"
            raise ValueError(msg)


def _check_global_name(name: str, kind: str) -> None:
    if name in _REGISTRY:
        what = "session" if isinstance(_REGISTRY[name], Func) else "environment"
        msg = f"A {what} named {name!r} is already registered; cannot register {kind} {name!r}."
        raise ValueError(msg)
    if name in _ALIASES:
        msg = f"An alias named {name!r} is already registered; cannot register {kind} {name!r}."
        raise ValueError(msg)


def register_env(environment: Environment) -> None:
    """Register an environment."""
    validate_name(environment.name)
    _check_global_name(environment.name, "environment")
    _REGISTRY[environment.name] = environment
    _TASKS[environment.name] = {}


def register_task(environment: Environment, task_name: str, fn: Func) -> None:
    """Register a task under its environment."""
    if _REGISTRY.get(environment.name) is not environment:
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


def alias(name: str, /, *targets: str) -> None:
    """Register a global alias that expands to one or more sessions.

    Args:
        name: The alias name; shares a namespace with sessions and
            environments.
        targets: One or more session identifiers (e.g. ``"tooling:lint"``).
    """
    validate_name(name, "An alias")
    if not targets:
        msg = f"Alias {name!r} needs at least one target."
        raise ValueError(msg)
    _check_global_name(name, "alias")
    _ALIASES[name] = targets


@overload
def session_decorator(func: RawFunc | Func, /) -> Func: ...


@overload
def session_decorator(
    func: None = ...,
    /,
    python: Python | None = ...,
    py: Python | None = ...,
    reuse_venv: bool | None = ...,  # noqa: FBT001
    name: str | None = ...,
    venv_backend: str | None = ...,
    venv_params: Sequence[str] = ...,
    tags: Sequence[str] | None = ...,
    *,
    default: bool = ...,
    requires: Sequence[str] | None = ...,
    download_python: Literal["auto", "never", "always"] | None = None,
    allow_parallel: bool | None = ...,
) -> Callable[[RawFunc | Func], Func]: ...


def session_decorator(
    func: Callable[..., Any] | Func | None = None,
    /,
    python: Python | None = None,
    py: Python | None = None,
    reuse_venv: bool | None = None,  # noqa: FBT001
    name: str | None = None,
    venv_backend: str | None = None,
    venv_params: Sequence[str] = (),
    tags: Sequence[str] | None = None,
    *,
    default: bool = True,
    requires: Sequence[str] | None = None,
    download_python: Literal["auto", "never", "always"] | None = None,
    allow_parallel: bool | None = None,
) -> Func | Callable[[RawFunc | Func], Func]:
    """Designate the decorated function as a session."""
    # If `func` is provided, then this is the decorator call with the function
    # being sent as part of the Python syntax (`@nox.session`).
    # If `func` is None, however, then this is a plain function call, and it
    # must return the decorator that ultimately is applied
    # (`@nox.session(...)`).
    #
    # This is what makes the syntax with and without parentheses both work.
    if func is None:
        return functools.partial(
            session_decorator,
            python=python,
            py=py,
            reuse_venv=reuse_venv,
            name=name,
            venv_backend=venv_backend,
            venv_params=venv_params,
            tags=tags,
            default=default,
            requires=requires,
            download_python=download_python,
            allow_parallel=allow_parallel,
        )

    if isinstance(func, Func):
        func = func.func

    if py is not None and python is not None:
        msg = (
            "The py argument to nox.session is an alias for the python "
            "argument, please only specify one."
        )
        raise ValueError(msg)

    if python is None:
        python = py

    reg_name = name or func.__name__

    if any(char in reg_name for char in ":()"):
        msg = (
            f"The session name {reg_name!r} contains characters used by "
            "environment:task identifiers (':', '(', ')'); this will become "
            "an error in a future version of nox."
        )
        warnings.warn(msg, FutureWarning, stacklevel=2)

    fn = Func(
        func,
        python,
        reuse_venv,
        reg_name,
        venv_backend,
        venv_params,
        tags=tags,
        default=default,
        requires=requires,
        download_python=download_python,
        allow_parallel=allow_parallel,
    )

    # Session names are not validated: they predate the env:task grammar.
    if reg_name in _TASKS:
        msg = (
            f"An environment named {reg_name!r} is already registered; "
            "sessions and environments share one namespace."
        )
        raise ValueError(msg)
    if reg_name in _ALIASES:
        msg = (
            f"An alias named {reg_name!r} is already registered; "
            "sessions and aliases share one namespace."
        )
        raise ValueError(msg)
    if reg_name in _REGISTRY:
        msg = (
            f"The session {reg_name!r} has already been registered; "
            "this will be an error in a future version of nox. "
            "Overriding the old session for now."
        )
        warnings.warn(msg, FutureWarning, stacklevel=2)
    _REGISTRY[reg_name] = fn
    return fn
