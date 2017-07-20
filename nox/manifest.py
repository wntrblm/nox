# Copyright 2017 Jon Wayne Parrott
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

from __future__ import absolute_import
import copy
import itertools

from nox._parametrize import generate_calls
from nox.logger import logger
from nox.sessions import Session


class Manifest(object):
    """Session manifest.

    The session manifest provides the final list of sessions that should be
    run by nox.

    It is possible for this to be mutated during execution. This allows for
    useful use cases, such as for one session to "notify" another.

    Args:
        session_functions (Mapping[str, function]): The registry of discovered
            session functions.
        global_config (): The global configuration.
    """
    def __init__(self, session_functions, global_config):
        self._all_sessions = []
        self._config = global_config

        # Create the sessions based on the provided session functions.
        for name, func in session_functions.items():
            self.make_session(name, func)

        # By default, every available session starts off in the queue.
        self._queue = copy.copy(self._all_sessions)
        self._consumed = []

        # If the configuration specified filters, apply those now.
        if self._config.sessions:
            self.filter_by_name(self._config.sessions)
        if self._config.keywords:
            self.filter_by_keywords(self._config.keywords)

    def __iter__(self):
        return self

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

    def __nonzero__(self):
        return bool(self._queue) or bool(self._consumed)

    def filter_by_name(self, specified_sessions):
        """Filter sessions in the queue based on the user-specified names.

        Args:
            specified_sessions (Sequence[str]): A list of specified
                session names.
        """
        # Filter the sessions remaining in the queue based on
        # whether they are individually specified.
        self._queue = [x for x in self._queue if (
            x.name in specified_sessions or
            x.signature in specified_sessions)]

        # If a session was requested and was not found, complain loudly.
        missing_sessions = set(specified_sessions) - set(
            itertools.chain(
                [x.name for x in self._all_sessions if x.name],
                [x.signature for x in self._all_sessions if x.signature]))
        if missing_sessions:
            logger.error('Sessions {} not found.'.format(', '.join(
                missing_sessions)))
            return False

    def filter_by_keywords(self, keywords):
        """Filter sessions using pytest-like keyword expressions.

        Args:
            keywords (Collection[str]): A collection of keywords which
                session names are checked against.
        """
        self._queue = [
            x for x in self._queue
            if keyword_match(keywords, [x.signature or x.name])]

    def make_session(self, name, func):
        """Create a session object from the session function.

        Args:
            name (str): The name of the session.
            func (function): The session function.

        Returns:
            nox.sessions.Session: A session object. The object is also
                automatically added to the manifest.
        """
        if not hasattr(func, 'parametrize'):
            session = Session(name, None, func, self._config, self)
            self._all_sessions.append(session)
        else:
            calls = generate_calls(func, func.parametrize)
            for call in calls:
                long_name = name + call.session_signature
                session = Session(name, long_name, call, self._config, self)
                self._all_sessions.append(session)
            if not calls:
                # Add an empty, do-nothing session.
                session = Session(
                    name, None, _null_session_func, self._config, self)
                self._all_sessions.append(session)
        return session

    def next(self):
        return self.__next__()


class KeywordLocals(object):
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
    """A do-nothing session for patemetrized sessions that have no available
    parameters."""
    session.skip('This session had no parameters available.')
