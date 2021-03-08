# Copyright 2021 Alethea Katherine Flowers
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

from pathlib import Path
from textwrap import dedent
from typing import Optional

import pytest
from nox import needs_version
from nox._version import (
    InvalidVersionSpecifier,
    VersionCheckFailed,
    _parse_needs_version,
    check_nox_version,
    get_nox_version,
)


@pytest.fixture
def temp_noxfile(tmp_path: Path):
    def make_temp_noxfile(content: str) -> str:
        path = tmp_path / "noxfile.py"
        path.write_text(content)
        return str(path)

    return make_temp_noxfile


def test_needs_version_default() -> None:
    """It is None by default."""
    assert needs_version is None


def test_get_nox_version() -> None:
    """It returns something that looks like a Nox version."""
    result = get_nox_version()
    year, month, day = [int(part) for part in result.split(".")[:3]]
    assert year >= 2020


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", None),
        (
            dedent(
                """
                import nox
                nox.needs_version = '>=2020.12.31'
                """
            ),
            ">=2020.12.31",
        ),
        (
            dedent(
                """
                import nox
                nox.needs_version = 'bogus'
                nox.needs_version = '>=2020.12.31'
                """
            ),
            ">=2020.12.31",
        ),
        (
            dedent(
                """
                import nox.sessions
                nox.needs_version = '>=2020.12.31'
                """
            ),
            ">=2020.12.31",
        ),
        (
            dedent(
                """
                import nox as _nox
                _nox.needs_version = '>=2020.12.31'
                """
            ),
            None,
        ),
    ],
)
def test_parse_needs_version(text: str, expected: Optional[str]) -> None:
    """It is parsed successfully."""
    assert expected == _parse_needs_version(text)


@pytest.mark.parametrize("specifiers", ["", ">=2020.12.31", ">=2020.12.31,<9999.99.99"])
def test_check_nox_version_succeeds(temp_noxfile, specifiers: str) -> None:
    """It does not raise if the version specifiers are satisfied."""
    text = dedent(
        f"""
        import nox
        nox.needs_version = "{specifiers}"
        """
    )
    check_nox_version(temp_noxfile(text))


@pytest.mark.parametrize("specifiers", [">=9999.99.99"])
def test_check_nox_version_fails(temp_noxfile, specifiers: str) -> None:
    """It raises an exception if the version specifiers are not satisfied."""
    text = dedent(
        f"""
        import nox
        nox.needs_version = "{specifiers}"
        """
    )
    with pytest.raises(VersionCheckFailed):
        check_nox_version(temp_noxfile(text))


@pytest.mark.parametrize("specifiers", ["invalid", "2020.12.31"])
def test_check_nox_version_invalid(temp_noxfile, specifiers: str) -> None:
    """It raises an exception if the version specifiers cannot be parsed."""
    text = dedent(
        f"""
        import nox
        nox.needs_version = "{specifiers}"
        """
    )
    with pytest.raises(InvalidVersionSpecifier):
        check_nox_version(temp_noxfile(text))
