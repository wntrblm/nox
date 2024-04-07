from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

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
