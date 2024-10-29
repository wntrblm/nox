from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import packaging.specifiers

if TYPE_CHECKING:
    from typing import Any

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


__all__ = ["load_toml", "python_versions"]


def __dir__() -> list[str]:
    return __all__


# Note: the implementation (including this regex) taken from PEP 723
# https://peps.python.org/pep-0723

REGEX = re.compile(
    r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"
)


def load_toml(filename: os.PathLike[str] | str) -> dict[str, Any]:
    """
    Load a toml file or a script with a PEP 723 script block.

    The file must have a ``.toml`` extension to be considered a toml file or a
    ``.py`` extension / no extension to be considered a script. Other file
    extensions are not valid in this function.

    Example:

    .. code-block:: python

        @nox.session
        def myscript(session):
            myscript_options = nox.project.load_toml("myscript.py")
            session.install(*myscript_options["dependencies"])
    """
    filepath = Path(filename)
    if filepath.suffix == ".toml":
        return _load_toml_file(filepath)
    if filepath.suffix in {".py", ""}:
        return _load_script_block(filepath)
    msg = f"Extension must be .py or .toml, got {filepath.suffix}"
    raise ValueError(msg)


def _load_toml_file(filepath: Path) -> dict[str, Any]:
    with filepath.open("rb") as f:
        return tomllib.load(f)


def _load_script_block(filepath: Path) -> dict[str, Any]:
    name = "script"
    script = filepath.read_text(encoding="utf-8")
    matches = list(filter(lambda m: m.group("type") == name, REGEX.finditer(script)))

    if not matches:
        raise ValueError(f"No {name} block found in {filepath}")
    if len(matches) > 1:
        raise ValueError(f"Multiple {name} blocks found in {filepath}")

    content = "".join(
        line[2:] if line.startswith("# ") else line[1:]
        for line in matches[0].group("content").splitlines(keepends=True)
    )
    return tomllib.loads(content)


def python_versions(
    pyproject: dict[str, Any], *, max_version: str | None = None
) -> list[str]:
    """
    Read a list of supported Python versions. Without ``max_version``, this
    will read the trove classifiers (recommended). With a ``max_version``, it
    will read the requires-python setting for a lower bound, and will use the
    value of ``max_version`` as the upper bound. (Reminder: you should never
    set an upper bound in ``requires-python``).

    Example:

    .. code-block:: python

        import nox

        PYPROJECT = nox.project.load_toml("pyproject.toml")
        # From classifiers
        PYTHON_VERSIONS = nox.project.python_versions(PYPROJECT)
        # Or from requires-python
        PYTHON_VERSIONS = nox.project.python_versions(PYPROJECT, max_version="3.13")
    """
    if max_version is None:
        # Classifiers are a list of every Python version
        from_classifiers = [
            c.split()[-1]
            for c in pyproject.get("project", {}).get("classifiers", [])
            if c.startswith("Programming Language :: Python :: 3.")
        ]
        if from_classifiers:
            return from_classifiers
        raise ValueError('No Python version classifiers found in "project.classifiers"')

    requires_python_str = pyproject.get("project", {}).get("requires-python", "")
    if not requires_python_str:
        raise ValueError('No "project.requires-python" value set')

    for spec in packaging.specifiers.SpecifierSet(requires_python_str):
        if spec.operator in {">", ">=", "~="}:
            min_minor_version = int(spec.version.split(".")[1])
            break
    else:
        raise ValueError('No minimum version found in "project.requires-python"')

    max_minor_version = int(max_version.split(".")[1])

    return [f"3.{v}" for v in range(min_minor_version, max_minor_version + 1)]
