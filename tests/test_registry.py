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

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pytest

import nox
from nox import registry

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def cleanup_registry() -> Generator[None, None, None]:
    """Ensure that the session registry is completely empty before and
    after each test.
    """
    try:
        registry._REGISTRY.clear()
        yield
    finally:
        registry._REGISTRY.clear()


def test_session_decorator() -> None:
    # Establish that the use of the session decorator will cause the
    # function to be found in the registry.
    @registry.session_decorator
    def unit_tests(session: nox.Session) -> None:
        pass

    answer = registry.get()
    assert "unit_tests" in answer
    assert answer["unit_tests"] is unit_tests
    assert unit_tests.python is None


def test_session_decorator_single_python() -> None:
    @registry.session_decorator(python="3.6")
    def unit_tests(session: nox.Session) -> None:
        pass

    assert unit_tests.python == "3.6"


def test_session_decorator_list_of_pythons() -> None:
    @registry.session_decorator(python=["3.5", "3.6"])
    def unit_tests(session: nox.Session) -> None:
        pass

    assert unit_tests.python == ["3.5", "3.6"]


def test_session_decorator_tags() -> None:
    @registry.session_decorator(tags=["tag-1", "tag-2"])
    def unit_tests(session: nox.Session) -> None:
        pass

    assert unit_tests.tags == ["tag-1", "tag-2"]


def test_session_decorator_py_alias() -> None:
    @registry.session_decorator(py=["3.5", "3.6"])
    def unit_tests(session: nox.Session) -> None:
        pass

    assert unit_tests.python == ["3.5", "3.6"]


def test_session_decorator_py_alias_error() -> None:
    with pytest.raises(ValueError, match="argument"):

        @registry.session_decorator(python=["3.5", "3.6"], py="2.7")
        def unit_tests(session: nox.Session) -> None:
            pass


def test_session_decorator_reuse() -> None:
    @registry.session_decorator(reuse_venv=True)
    def unit_tests(session: nox.Session) -> None:
        pass

    assert unit_tests.reuse_venv is True


@pytest.mark.parametrize("name", ["unit-tests", "unit tests", "the unit tests"])
def test_session_decorator_name(
    name: Literal["unit-tests", "unit tests", "the unit tests"],
) -> None:
    @registry.session_decorator(name=name)
    def unit_tests(session: nox.Session) -> None:
        pass

    answer = registry.get()
    assert "unit_tests" not in answer
    assert name in answer
    assert answer[name] is unit_tests
    assert unit_tests.python is None


def test_get() -> None:
    # Establish that the get method returns a copy of the registry.
    empty = registry.get()
    assert empty == registry._REGISTRY
    assert empty is not registry._REGISTRY
    assert len(empty) == 0

    @registry.session_decorator
    def unit_tests(session: nox.Session) -> None:
        pass

    @registry.session_decorator
    def system_tests(session: nox.Session) -> None:
        pass

    full = registry.get()
    assert empty != full
    assert len(empty) == 0
    assert len(full) == 2
    assert full == registry._REGISTRY
    assert full is not registry._REGISTRY
    assert full["unit_tests"] is unit_tests
    assert full["system_tests"] is system_tests
