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

from nox.registry import session_decorator
from nox.registry import SessionRegistry

import pytest


@pytest.fixture
def cleanup_registry():
    """Ensure that the session registry is completely empty before and
    after each test.
    """
    try:
        SessionRegistry.clear()
        yield
    finally:
        SessionRegistry.clear()


def test_session_registry_singleton(cleanup_registry):
    # Establish that multiple calls to SessionRegistry.get_registry
    # with the same arguments consistently return the same objects.
    assert SessionRegistry.get('foo') is SessionRegistry.get('foo')
    assert SessionRegistry.get('bar') is SessionRegistry.get('bar')
    assert SessionRegistry.get('foo') is not SessionRegistry.get('bar')


def test_multi_init_failure(cleanup_registry):
    # Establish that if __init__ is called more than once with the same
    # code, that it fails rather than plowing over data.
    assert 'foo' not in SessionRegistry._meta_registry
    SessionRegistry.get('foo')
    assert 'foo' in SessionRegistry._meta_registry
    with pytest.raises(ValueError):
        SessionRegistry('foo')


def test_registry_repr(cleanup_registry):
    # Establish that the SessionRegistry has a friendly repr, for debugging.
    foo_registry = SessionRegistry.get('foo')
    foo_registry['unit'] = lambda session: None
    assert '<SessionRegistry' in repr(foo_registry)
    assert "'unit'" in repr(foo_registry)


def test_registry_iteration(cleanup_registry):
    # Establish that the various iteration methods work correctly.
    foo = SessionRegistry.get('foo')
    foo['unit_tests'] = lambda session: None
    foo['system_tests'] = lambda session: None
    assert [key for key in foo] == ['unit_tests', 'system_tests']
    assert [key for key in foo.keys()] == ['unit_tests', 'system_tests']
    assert all([callable(func) for func in foo.values()])
    for key, value in foo.items():
        assert key.endswith('_tests')
        assert callable(value)


def test_registry_getitem(cleanup_registry):
    # Establish that the registry's __getitem__ pulls from the
    # dictionary it contains.
    foo = SessionRegistry.get('foo')

    def func(session):
        pass
    foo['unit_tests'] = func
    assert foo['unit_tests'] == foo._sessions['unit_tests'] == func


def test_session_decorator(cleanup_registry):
    # Establish that the use of the session decorator will cause the
    # function to be found in the registry.
    @session_decorator
    def unit_tests(session):
        pass

    registry = SessionRegistry.get(unit_tests.__module__)
    assert 'unit_tests' in registry
    assert registry['unit_tests'] == unit_tests
