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

_REGISTRY = collections.OrderedDict()


def session_decorator(
    func=None, python=None, py=None, reuse_venv=None, run_by_default=None
):
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
            run_by_default=run_by_default,
        )

    if py is not None and python is not None:
        raise ValueError(
            "The py argument to nox.session is an alias for the python "
            "argument, please only specify one."
        )

    if python is None:
        python = py

    func.python = python
    func.reuse_venv = reuse_venv
    func.run_by_default = run_by_default
    _REGISTRY[func.__name__] = func

    return func


def get():
    """Return a shallow copy of the registry.

    This ensures that the registry is not accidentally modified by
    calling code that retrieves a registry and mutates it.
    """
    return copy.copy(_REGISTRY)
