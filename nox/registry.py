from __future__ import absolute_import

import collections
import copy


_REGISTRY = collections.OrderedDict()


def session_decorator(func):
    """Designate the wrapped function as a session.

    This adds the given function to the _REGISTRY ordered dictionary, which
    is checked by `nox.main.discover_session_functions`.
    """
    _REGISTRY[func.__name__] = func
    return func


def get():
    """Return a shallow copy of the registry.

    This ensures that the reigstry is not accidentally modified by
    calling code that retrieves a registry and mutates it.
    """
    return copy.copy(_REGISTRY)
