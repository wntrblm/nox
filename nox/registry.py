from __future__ import absolute_import

import collections
import copy

import six


class SessionRegistry(object):
    """A registry of nox session functions.

    Functions are added to the registry using the @nox.session
    decorator, rather than calling registry functions directly.
    """
    _meta_registry = {}
    """A registry of registered registries."""

    @classmethod
    def clear(cls):
        """Clear the meta-registry completely.

        This will wipe out the entire meta-registry. Primarily useful
        for ensuring independent test functions.
        """
        cls._meta_registry.clear()

    @classmethod
    def get(cls, code):
        """Retrieve the given registry.

        If the registry does not already exist, create an empty registry
        and return it.
        """
        if code in cls._meta_registry:
            return cls._meta_registry[code]
        return cls(code=code)

    def __init__(self, code):
        """Initialize the registry.

        This saves the registry to the meta-registry and adds an ordered
        dictionary of individual session functions.
        """
        # Sanity check: Do not plow over an existing registry.
        if code in self._meta_registry:
            raise ValueError('Attempt to create a duplicate registry. '
                             'Use `SessionRegistry.get_registry(code)`.')

        # Save the registry to the meta-registry.
        self._meta_registry[code] = self

        # Create an ordered dictionary in which to store session
        # functions.
        self._sessions = collections.OrderedDict()

    def __repr__(self):
        return '<SessionRegistry %r>' % self._sessions

    def __getitem__(self, key):
        return self._sessions[key]

    def __setitem__(self, key, value):
        self._sessions[key] = value

    def __iter__(self):
        return iter(self.sessions)

    @property
    def sessions(self):
        """Return a shallow copy of the `_sessions` ordered dictionary.

        This allows the copy to be mutated without affecting the contents
        of the registry.
        """
        return copy.copy(self._sessions)

    def items(self):
        return six.iteritems(self._sessions)

    def keys(self):
        return six.iterkeys(self._sessions)

    def values(self):
        return six.itervalues(self._sessions)


def session_decorator(func):
    """Designate the wrapped function as a session.

    This adds the given function to the SessionRegistry for that module, which
    is checked by `nox.main.discover_session_functions`.
    """
    SessionRegistry.get(func.__module__)[func.__name__] = func
    return func
