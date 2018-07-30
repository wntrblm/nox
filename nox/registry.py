from __future__ import absolute_import

import collections
import copy
import functools

_REGISTRY = collections.OrderedDict()


def session_decorator(
        func=None, python=None, reuse_venv=None):
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
            session_decorator, python=python, reuse_venv=reuse_venv)

    func.python = python
    func.reuse_venv = reuse_venv
    _REGISTRY[func.__name__] = func

    return func


def get():
    """Return a shallow copy of the registry.

    This ensures that the registry is not accidentally modified by
    calling code that retrieves a registry and mutates it.
    """
    return copy.copy(_REGISTRY)
