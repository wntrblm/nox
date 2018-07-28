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

import pytest

from nox import registry


@pytest.fixture
def cleanup_registry():
    """Ensure that the session registry is completely empty before and
    after each test.
    """
    try:
        registry._REGISTRY.clear()
        yield
    finally:
        registry._REGISTRY.clear()


def test_session_decorator(cleanup_registry):
    # Establish that the use of the session decorator will cause the
    # function to be found in the registry.
    @registry.session_decorator
    def unit_tests(session):
        pass

    answer = registry.get()
    assert 'unit_tests' in answer
    assert answer['unit_tests'] is unit_tests
    assert isinstance(unit_tests.python_config, registry.PythonConfig)


def test_session_decorator_single_string_python(cleanup_registry):
    @registry.session_decorator(python='3.6')
    def unit_tests(session):
        pass

    assert isinstance(unit_tests.python_config, registry.PythonConfig)
    assert unit_tests.python_config.python == '3.6'


def test_session_decorator_list_string_python(cleanup_registry):
    @registry.session_decorator(python=['3.5', '3.6'])
    def unit_tests(session):
        pass

    assert isinstance(unit_tests.python_config, list)
    assert len(unit_tests.python_config) == 2
    assert unit_tests.python_config[0].python == '3.5'
    assert unit_tests.python_config[1].python == '3.6'


def test_session_decorator_list_mixed(cleanup_registry):
    @registry.session_decorator(
        python=[
            '3.5',
            registry.PythonConfig(python='3.6', reuse=True)])
    def unit_tests(session):
        pass

    assert isinstance(unit_tests.python_config, list)
    assert len(unit_tests.python_config) == 2
    assert unit_tests.python_config[0].python == '3.5'
    assert unit_tests.python_config[0].reuse is None
    assert unit_tests.python_config[1].python == '3.6'
    assert unit_tests.python_config[1].reuse is True


def test_get(cleanup_registry):
    # Establish that the get method returns a copy of the registry.
    empty = registry.get()
    assert empty == registry._REGISTRY
    assert empty is not registry._REGISTRY
    assert len(empty) == 0

    @registry.session_decorator
    def unit_tests(session):
        pass

    @registry.session_decorator
    def system_tests(session):
        pass

    full = registry.get()
    assert empty != full
    assert len(empty) == 0
    assert len(full) == 2
    assert full == registry._REGISTRY
    assert full is not registry._REGISTRY
    assert full['unit_tests'] is unit_tests
    assert full['system_tests'] is system_tests
