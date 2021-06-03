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

import ast
import contextlib
import sys
from typing import Optional

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

if sys.version_info >= (3, 8):  # pragma: no cover
    import importlib.metadata as metadata
else:  # pragma: no cover
    import importlib_metadata as metadata


class VersionCheckFailed(Exception):
    """The Nox version does not satisfy what ``nox.needs_version`` specifies."""


class InvalidVersionSpecifier(Exception):
    """The ``nox.needs_version`` specifier cannot be parsed."""


def get_nox_version() -> str:
    """Return the version of the installed Nox package."""
    return metadata.version("nox")


def _parse_string_constant(node: ast.AST) -> Optional[str]:  # pragma: no cover
    """Return the value of a string constant."""
    if sys.version_info < (3, 8):
        if isinstance(node, ast.Str) and isinstance(node.s, str):
            return node.s
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _parse_needs_version(source: str, filename: str = "<unknown>") -> Optional[str]:
    """Parse ``nox.needs_version`` from the user's noxfile."""
    value: Optional[str] = None
    module: ast.Module = ast.parse(source, filename=filename)
    for statement in module.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "nox"
                    and target.attr == "needs_version"
                ):
                    value = _parse_string_constant(statement.value)
    return value


def _read_needs_version(filename: str) -> Optional[str]:
    """Read ``nox.needs_version`` from the user's noxfile."""
    with open(filename) as io:
        source = io.read()

    return _parse_needs_version(source, filename=filename)


def _check_nox_version_satisfies(needs_version: str) -> None:
    """Check if the Nox version satisfies the given specifiers."""
    version = Version(get_nox_version())

    try:
        specifiers = SpecifierSet(needs_version)
    except InvalidSpecifier as error:
        message = f"Cannot parse `nox.needs_version`: {error}"
        with contextlib.suppress(InvalidVersion):
            Version(needs_version)
            message += f", did you mean '>= {needs_version}'?"
        raise InvalidVersionSpecifier(message)

    if not specifiers.contains(version, prereleases=True):
        raise VersionCheckFailed(
            f"The Noxfile requires Nox {specifiers}, you have {version}"
        )


def check_nox_version(filename: str) -> None:
    """Check if ``nox.needs_version`` in the user's noxfile is satisfied.

    Args:

        filename: The location of the user's noxfile. ``nox.needs_version`` is
            read from the noxfile by parsing the AST.

    Raises:
        VersionCheckFailed: The Nox version does not satisfy what
            ``nox.needs_version`` specifies.
        InvalidVersionSpecifier: The ``nox.needs_version`` specifier cannot be
            parsed.
    """
    needs_version = _read_needs_version(filename)

    if needs_version is not None:
        _check_nox_version_satisfies(needs_version)
