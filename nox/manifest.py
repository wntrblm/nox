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

import copy
import functools
import itertools
import types

from nox._parametrize import generate_calls
from nox.sessions import SessionRunner


def _copy_func(src, name=None):
    dst = types.FunctionType(
        src.__code__,
        src.__globals__,
        name=name or src.__name__,
        argdefs=src.__defaults__,
        closure=src.__closure__,
    )
    dst.__dict__.update(copy.deepcopy(src.__dict__))
    dst = functools.update_wrapper(dst, src)
    dst.__kwdefaults__ = src.__kwdefaults__
    return dst


class Manifest:
    """Session manifest.

    The session manifest provides the source of truth for the sequence of
    sessions that should be run by nox.

    It is possible for this to be mutated during execution. This allows for
    useful use cases, such as for one session to "notify" another or
    "chain" to another.

    Args:
        session_functions (Mapping[str, function]): The registry of discovered
            session functions.
        global_config (.nox.main.GlobalConfig): The global configuration.
    """

    def __init__(self, session_functions, global_config):
        self._all_sessions = []
        self._queue = []
        self._consumed = []
        self._config = global_config

        # Create the sessions based on the provided session functions.
        for name, func in session_functions.items():
            for session in self.make_session(name, func):
                self.add_session(session)

    def __contains__(self, needle):
        if needle in self._queue or needle in self._consumed:
            return True
        for session in self._queue + self._consumed:
            if session.name == needle or session.signature == needle:
                return True
        return False

    def __iter__(self):
        return self

    def __getitem__(self, key):
        for session in self._queue + self._consumed:
            if session.name == key or session.signature == key:
                return session
        raise KeyError(key)

    def __next__(self):
        """Return the next item in the queue.

        Raises:
            StopIteration: If the queue has been entirely consumed.
        """
        if not len(self._queue):
            raise StopIteration
        session = self._queue.pop(0)
        self._consumed.append(session)
        return session

    def __len__(self):
        return len(self._queue) + len(self._consumed)

    def add_session(self, session):
        """Add the given session to the manifest.

        Args:
            session (~nox.sessions.Session): A session object, such as
                one returned from ``make_session``.
        """
        if session not in self._all_sessions:
            self._all_sessions.append(session)
        if session not in self._queue:
            self._queue.append(session)

    def filter_by_name(self, specified_sessions):
        """Filter sessions in the queue based on the user-specified names.

        Args:
            specified_sessions (Sequence[str]): A list of specified
                session names.

        Raises:
            KeyError: If any explicitly listed sessions are not found.
        """
        # Filter the sessions remaining in the queue based on
        # whether they are individually specified.
        self._queue = [
            x
            for x in self._queue
            if (x.name in specified_sessions or x.signature in specified_sessions)
        ]

        # If a session was requested and was not found, complain loudly.
        missing_sessions = set(specified_sessions) - set(
            itertools.chain(
                [x.name for x in self._all_sessions if x.name],
                [x.signature for x in self._all_sessions if x.signature],
            )
        )
        if missing_sessions:
            raise KeyError("Sessions not found: {}".format(", ".join(missing_sessions)))

    def filter_by_keywords(self, keywords):
        """Filter sessions using pytest-like keyword expressions.

        Args:
            keywords (str): A Python expression of keywords which
                session names are checked against.
        """
        self._queue = [
            x for x in self._queue if keyword_match(keywords, [x.signature or x.name])
        ]

    def make_session(self, name, func):
        """Create a session object from the session function.

        Args:
            name (str): The name of the session.
            func (function): The session function.

        Returns:
            Sequence[~nox.session.Session]: A sequence of Session objects
                bound to this manifest and configuration.
        """
        sessions = []

        # If the func has the python attribute set to a list, we'll need
        # to expand them.
        if isinstance(func.python, (list, tuple, set)):
            for python in func.python:
                single_func = _copy_func(func)
                single_func.python = python
                sessions.extend(self.make_session(name, single_func))

            return sessions

        # Simple case: If this function is not parametrized, then make
        # a simple session
        if not hasattr(func, "parametrize"):
            if func.python:
                long_name = "{}-{}".format(name, func.python)
            else:
                long_name = name
            session = SessionRunner(name, long_name, func, self._config, self)
            return [session]

        # Since this function is parametrized, we need to add a distinct
        # session for each permutation.
        calls = generate_calls(func, func.parametrize)
        for call in calls:
            if func.python:
                long_name = "{}-{}{}".format(name, func.python, call.session_signature)
            else:
                long_name = "{}{}".format(name, call.session_signature)

            sessions.append(SessionRunner(name, long_name, call, self._config, self))

        # Edge case: If the parameters made it such that there were no valid
        # calls, add an empty, do-nothing session.
        if not calls:
            sessions.append(
                SessionRunner(name, None, _null_session_func, self._config, self)
            )

        # Return the list of sessions.
        return sessions

    def next(self):
        return self.__next__()

    def notify(self, session):
        """Enqueue the specified session in the queue.

        If the session is already in the queue, or has been run already,
        then this is a no-op.

        Args:
            session (Union[str, ~nox.session.Session]): The session to be
                enqueued.

        Returns:
            bool: Whether the session was added to the queue.

        Raises:
            ValueError: If the session was not found.
        """
        # Sanity check: If this session is already in the queue, this is
        # a no-op.
        if session in self:
            return False

        # Locate the session in the list of all sessions, and place it at
        # the end of the queue.
        for s in self._all_sessions:
            if s == session or s.name == session or s.signature == session:
                self._queue.append(s)
                return True

        # The session was not found in the list of sessions.
        raise ValueError("Session %s not found." % session)


class KeywordLocals:
    """Eval locals using keywords.

    When looking up a local variable the variable name is compared against
    the set of keywords. If the local variable name matches any *substring* of
    any keyword, then the name lookup returns True. Otherwise, the name lookup
    returns False.
    """

    def __init__(self, keywords):
        self._keywords = keywords

    def __getitem__(self, variable_name):
        for keyword in self._keywords:
            if variable_name in keyword:
                return True
        return False


def keyword_match(expression, keywords):
    """See if an expression matches the given set of keywords."""
    locals = KeywordLocals(set(keywords))
    return eval(expression, {}, locals)


def _null_session_func(session):
    """A no-op session for patemetrized sessions with no available params."""
    session.skip("This session had no parameters available.")
