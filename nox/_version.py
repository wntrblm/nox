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
import sys
from typing import Optional

try:
    import importlib.metadata as metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata


def get_nox_version() -> str:
    """Return the version of the installed Nox package."""
    return metadata.version("nox")


def _parse_string_constant(node: ast.AST) -> Optional[str]:
    """Return the value of a string constant."""
    if sys.version_info < (3, 8):  # pragma: no cover
        if isinstance(node, ast.Str) and isinstance(node.s, str):
            return node.s
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None  # pragma: no cover


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
