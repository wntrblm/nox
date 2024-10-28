from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import packaging.requirements
import packaging.specifiers

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any, TypeVar

    T = TypeVar("T")

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


__all__ = ["load_toml", "python_versions", "dependency_groups"]


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


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _normalize_group_names(dependency_groups: dict[str, T]) -> dict[str, T]:
    original_names: dict[str, list[str]] = {}
    normalized_groups = {}

    for group_name, value in dependency_groups.items():
        normed_group_name = _normalize_name(group_name)
        original_names.setdefault(normed_group_name, []).append(group_name)
        normalized_groups[normed_group_name] = value

    errors = []
    for normed_name, names in original_names.items():
        if len(names) > 1:
            errors.append(f"{normed_name} ({', '.join(names)})")
    if errors:
        raise ValueError(f"Duplicate dependency group names: {', '.join(errors)}")

    return normalized_groups


def _resolve_dependency_group(
    dependency_groups: dict[str, Any], group: str, *past_groups: str
) -> Generator[str, None, None]:
    if group in past_groups:
        raise ValueError(f"Cyclic dependency group include: {group} -> {past_groups}")

    if group not in dependency_groups:
        raise LookupError(f"Dependency group '{group}' not found")

    raw_group = dependency_groups[group]
    if not isinstance(raw_group, list):
        raise ValueError(f"Dependency group '{group}' is not a list")

    for item in raw_group:
        if isinstance(item, str):
            # packaging.requirements.Requirement parsing ensures that this is a valid
            # PEP 508 Dependency Specifier
            # raises InvalidRequirement on failure
            packaging.requirements.Requirement(item)
            yield item
        elif isinstance(item, dict):
            if tuple(item.keys()) != ("include-group",):
                raise ValueError(f"Invalid dependency group item: {item}")

            include_group = _normalize_name(next(iter(item.values())))
            yield from _resolve_dependency_group(
                dependency_groups, include_group, *past_groups, group
            )
        else:
            raise ValueError(f"Invalid dependency group item: {item}")


def _resolve(
    dependency_groups: dict[str, Any], *groups: str
) -> Generator[str, None, None]:
    if not isinstance(dependency_groups, dict):
        raise TypeError("Dependency Groups table is not a dict")
    for group in groups:
        if not isinstance(group, str):
            raise TypeError("Dependency group name is not a str")
        yield from _resolve_dependency_group(dependency_groups, group)


def dependency_groups(pyproject: dict[str, Any], *groups: str) -> list[str]:
    norm_groups = (_normalize_name(g) for g in groups)
    return list(_resolve(pyproject["dependency-groups"], *norm_groups))
