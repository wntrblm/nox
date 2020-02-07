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

import collections
import copy
import functools
from typing import Any, Callable, Optional, Sequence, Union

_REGISTRY = collections.OrderedDict()  # type: collections.OrderedDict[str, Callable]
Python = Optional[Union[str, Sequence[str], bool]]


def session_decorator(
    func: Optional[Callable] = None,
    python: Python = None,
    py: Python = None,
    reuse_venv: Optional[bool] = None,
    name: Optional[str] = None,
    venv_backend: Any = None,
    venv_params: Any = None,
) -> Callable:
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
        )

    if py is not None and python is not None:
        raise ValueError(
            "The py argument to nox.session is an alias for the python "
            "argument, please only specify one."
        )

    if python is None:
        python = py

    func.python = python  # type: ignore
    func.reuse_venv = reuse_venv  # type: ignore
    func.venv_backend = venv_backend  # type: ignore
    func.venv_params = venv_params  # type: ignore
    _REGISTRY[name or func.__name__] = func

    return func


def get() -> "collections.OrderedDict[str, Callable]":
    """Return a shallow copy of the registry.

    This ensures that the registry is not accidentally modified by
    calling code that retrieves a registry and mutates it.
    """
    return copy.copy(_REGISTRY)
