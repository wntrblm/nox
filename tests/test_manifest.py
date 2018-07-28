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
from unittest import mock

import pytest

import nox
from nox.manifest import _null_session_func
from nox.manifest import Manifest


def create_mock_sessions():
    sessions = collections.OrderedDict()
    sessions['foo'] = mock.Mock(
        spec=(), python_config=nox.registry.PythonConfig())
    sessions['bar'] = mock.Mock(
        spec=(), python_config=nox.registry.PythonConfig())
    return sessions


def test_init():
    sessions = create_mock_sessions()
    manifest = Manifest(sessions, mock.sentinel.CONFIG)

    # Assert that basic properties look correctly.
    assert len(manifest) == 2
    assert manifest['foo'].func is sessions['foo']
    assert manifest['bar'].func is sessions['bar']


def test_contains():
    sessions = create_mock_sessions()
    manifest = Manifest(sessions, mock.sentinel.CONFIG)

    # Establish that contains works pre-iteration.
    assert 'foo' in manifest
    assert 'bar' in manifest
    assert 'baz' not in manifest

    # Establish that __contains__ works post-iteration.
    for session in manifest:
        pass
    assert 'foo' in manifest
    assert 'bar' in manifest
    assert 'baz' not in manifest

    # Establish that sessions themselves work.
    assert manifest['foo'] in manifest


def test_getitem():
    sessions = create_mock_sessions()
    manifest = Manifest(sessions, mock.sentinel.CONFIG)

    # Establish that each session is present, and a made-up session
    # is not.
    assert manifest['foo'].func is sessions['foo']
    assert manifest['bar'].func is sessions['bar']
    with pytest.raises(KeyError):
        manifest['baz']

    # Establish that the sessions are still present even after being
    # consumed by iteration.
    for session in manifest:
        pass
    assert manifest['foo'].func is sessions['foo']
    assert manifest['bar'].func is sessions['bar']


def test_iteration():
    sessions = create_mock_sessions()
    manifest = Manifest(sessions, mock.sentinel.CONFIG)

    # There should be two sessions in the queue.
    assert len(manifest._queue) == 2
    assert len(manifest._consumed) == 0

    # The first item should be our "foo" session.
    foo = next(manifest)
    assert foo.func == sessions['foo']
    assert foo in manifest._consumed
    assert foo not in manifest._queue
    assert len(manifest._consumed) == 1
    assert len(manifest._queue) == 1

    # The .next() or .__next__() methods can be called directly according
    # to Python's data model.
    bar = manifest.next()
    assert bar.func == sessions['bar']
    assert bar in manifest._consumed
    assert bar not in manifest._queue
    assert len(manifest._consumed) == 2
    assert len(manifest._queue) == 0

    # Continuing past the end raises StopIteration.
    with pytest.raises(StopIteration):
        manifest.__next__()


def test_len():
    sessions = create_mock_sessions()
    manifest = Manifest(sessions, mock.sentinel.CONFIG)
    assert len(manifest) == 2
    for session in manifest:
        assert len(manifest) == 2


def test_filter_by_name():
    sessions = create_mock_sessions()
    manifest = Manifest(sessions, mock.sentinel.CONFIG)
    manifest.filter_by_name(('foo',))
    assert 'foo' in manifest
    assert 'bar' not in manifest


def test_filter_by_name_not_found():
    sessions = create_mock_sessions()
    manifest = Manifest(sessions, mock.sentinel.CONFIG)
    with pytest.raises(KeyError):
        manifest.filter_by_name(('baz',))


def test_filter_by_keyword():
    sessions = create_mock_sessions()
    manifest = Manifest(sessions, mock.sentinel.CONFIG)
    assert len(manifest) == 2
    manifest.filter_by_keywords('foo or bar')
    assert len(manifest) == 2
    manifest.filter_by_keywords('foo')
    assert len(manifest) == 1


def test_add_session_plain():
    manifest = Manifest({}, mock.sentinel.CONFIG)
    session_func = mock.Mock(
        spec=(), python_config=nox.registry.PythonConfig())
    for session in manifest.make_session('my_session', session_func):
        manifest.add_session(session)
    assert len(manifest) == 1


def test_add_session_multiple_pythons():
    manifest = Manifest({}, mock.sentinel.CONFIG)

    def session_func():
        pass

    session_func.python_config = [
        nox.registry.PythonConfig(python='3.6'),
        nox.registry.PythonConfig(python='3.7'),
    ]

    for session in manifest.make_session('my_session', session_func):
        manifest.add_session(session)

    assert len(manifest) == 2


def test_add_session_parametrized():
    manifest = Manifest({}, mock.sentinel.CONFIG)

    # Define a session with parameters.
    @nox.parametrize('param', ('a', 'b', 'c'))
    def my_session(session, param):
        pass

    my_session.python_config = nox.registry.PythonConfig()

    # Add the session to the manifest.
    for session in manifest.make_session('my_session', my_session):
        manifest.add_session(session)
    assert len(manifest) == 3


def test_add_session_parametrized_noop():
    manifest = Manifest({}, mock.sentinel.CONFIG)

    # Define a session without any parameters.
    @nox.parametrize('param', ())
    def my_session(session, param):
        pass

    my_session.python_config = nox.registry.PythonConfig()

    # Add the session to the manifest.
    for session in manifest.make_session('my_session', my_session):
        manifest.add_session(session)
    assert len(manifest) == 1


def test_notify():
    manifest = Manifest({}, mock.sentinel.CONFIG)

    # Define a session.
    def my_session(session):
        pass

    my_session.python_config = nox.registry.PythonConfig()

    def notified(session):
        pass

    notified.python_config = nox.registry.PythonConfig()

    # Add the sessions to the manifest.
    for session in manifest.make_session('my_session', my_session):
        manifest.add_session(session)
    for session in manifest.make_session('notified', notified):
        manifest.add_session(session)
    assert len(manifest) == 2

    # Filter so only the first session is included in the queue.
    manifest.filter_by_name(('my_session',))
    assert len(manifest) == 1

    # Notify the notified session.
    manifest.notify('notified')
    assert len(manifest) == 2


def test_notify_noop():
    manifest = Manifest({}, mock.sentinel.CONFIG)

    # Define a session and add it to the manifest.
    def my_session(session):
        pass

    my_session.python_config = nox.registry.PythonConfig()

    for session in manifest.make_session('my_session', my_session):
        manifest.add_session(session)

    assert len(manifest) == 1

    # Establish idempotency; notifying a session already in the queue no-ops.
    manifest.notify('my_session')
    assert len(manifest) == 1


def test_notify_error():
    manifest = Manifest({}, mock.sentinel.CONFIG)
    with pytest.raises(ValueError):
        manifest.notify('does_not_exist')


def test_add_session_idempotent():
    manifest = Manifest({}, mock.sentinel.CONFIG)
    session_func = mock.Mock(
        spec=(), python_config=nox.registry.PythonConfig())
    for session in manifest.make_session('my_session', session_func):
        manifest.add_session(session)
        manifest.add_session(session)
    assert len(manifest) == 1


def test_null_session_function():
    session = mock.Mock(spec=('skip',))
    _null_session_func(session)
    assert session.skip.called
