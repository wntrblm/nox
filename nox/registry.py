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

__lazy_modules__ = {
    f"{__spec__.parent}._decorators",
    f"{__spec__.parent}.environments",
    "functools",
    "warnings",
}

import functools
import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, overload

from . import environments
from ._decorators import Func
from .environments import Environment, RegistryData, alias

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ._typing import Python

__all__ = [
    "RegistryData",
    "alias",
    "get",
    "get_registry",
    "reset",
    "session_decorator",
]


def __dir__() -> list[str]:
    return __all__


RawFunc = Callable[..., Any]


def reset() -> None:
    environments.reset_registry()


def get_registry() -> RegistryData:
    """Return a shallow copy of the full registry."""
    return environments.get_registry_data()


def get() -> dict[str, Func]:
    """Return the registered sessions as a name-to-function mapping.

    Only includes classic sessions (same-name environment/task pairs), for
    backward compatibility. Use :func:`get_registry` for the full registry.
    """
    data = environments.get_registry_data()
    return {
        name: data.tasks[name][name]
        for name, env in data.envs.items()
        if env._session_compat and name in data.tasks.get(name, {})
    }


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
) -> Func | Callable[[RawFunc | Func], Func]:
    """Designate the decorated function as a session.

    A session is an environment and a task sharing one name.
    """
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
    )

    if reg_name in environments._ENVS:
        if not environments._ENVS[reg_name]._session_compat:
            msg = (
                f"An environment named {reg_name!r} is already registered; "
                "sessions and environments share one namespace."
            )
            raise ValueError(msg)
        msg = (
            f"The session {reg_name!r} has already been registered; "
            "this will be an error in a future version of nox. "
            "Overriding the old session for now."
        )
        # Overwriting below keeps the original registration order.
        warnings.warn(msg, FutureWarning, stacklevel=2)
    elif reg_name in environments._ALIASES:
        msg = (
            f"An alias named {reg_name!r} is already registered; "
            "sessions and aliases share one namespace."
        )
        raise ValueError(msg)

    env = Environment(reg_name, python=python, register=False)
    environments.register_session_pair(env, fn)
    return fn
