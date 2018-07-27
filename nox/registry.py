from __future__ import absolute_import

import collections
import copy
import functools

import attr

_REGISTRY = collections.OrderedDict()


@attr.s
class PythonConfig:
    python = attr.ib(default=None)
    virtualenv = attr.ib(default=None)
    reuse = attr.ib(default=None)


def _to_python_config(value):
    if not isinstance(value, PythonConfig):
        return PythonConfig(python=value)
    return value


def session_decorator(func=None, python=None):
    """Designate the decorated function as a session."""
    if func is None:
        return functools.partial(session_decorator, python=python)

    # This adds the given function to the _REGISTRY ordered dictionary, which
    # is checked by `nox.main.discover_session_functions`.
    if isinstance(python, collections.Collection):
        python = [_to_python_config(value) for value in python]
    else:
        python = _to_python_config(python)

    func.python_config = python
    _REGISTRY[func.__name__] = func

    return func


def get():
    """Return a shallow copy of the registry.

    This ensures that the reigstry is not accidentally modified by
    calling code that retrieves a registry and mutates it.
    """
    return copy.copy(_REGISTRY)
