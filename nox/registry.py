from __future__ import absolute_import

import collections
import copy
import functools


_REGISTRY = collections.OrderedDict()


def session_decorator(func=None, python=None):
    """Designate the decorated function as a session."""
    if func is None:
        return functools.partial(session_decorator, python=python)

    # This adds the given function to the _REGISTRY ordered dictionary, which
    # is checked by `nox.main.discover_session_functions`.
    func.python = python
    _REGISTRY[func.__name__] = func

    return func


def get():
    """Return a shallow copy of the registry.

    This ensures that the reigstry is not accidentally modified by
    calling code that retrieves a registry and mutates it.
    """
    return copy.copy(_REGISTRY)
