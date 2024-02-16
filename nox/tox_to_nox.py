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

"""Naively converts tox.ini files into noxfile.py files."""

from __future__ import annotations

import argparse
import os
import pkgutil
import re
from collections.abc import Iterator
from configparser import ConfigParser
from pathlib import Path
from subprocess import check_output
from typing import Any, Iterable

import jinja2
import tox.config
from tox import __version__ as TOX_VERSION

TOX4 = TOX_VERSION[0] == "4"

if TOX4:
    _TEMPLATE = jinja2.Template(
        pkgutil.get_data(__name__, "tox4_to_nox.jinja2").decode("utf-8"),  # type: ignore[union-attr]
        extensions=["jinja2.ext.do"],
    )
else:
    _TEMPLATE = jinja2.Template(
        pkgutil.get_data(__name__, "tox_to_nox.jinja2").decode("utf-8"),  # type: ignore[union-attr]
        extensions=["jinja2.ext.do"],
    )


def wrapjoin(seq: Iterator[Any]) -> str:
    """Wrap each item in single quotes and join them with a comma."""
    return ", ".join([f"'{item}'" for item in seq])


def fixname(envname: str) -> str:
    """Replace dashes with underscores and check if the result is a valid identifier."""
    envname = envname.replace("-", "_").replace("testenv:", "")
    if not envname.isidentifier():
        print(
            f"Environment {envname!r} is not a valid nox session name.\n"
            "Manually update the session name in noxfile.py before running nox."
        )
    return envname


def write_output_to_file(output: str, filename: str) -> None:
    """Write output to a file."""
    with open(filename, "w") as outfile:
        outfile.write(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Converts toxfiles to noxfiles.")
    parser.add_argument("--output", default="noxfile.py")

    args = parser.parse_args()

    if TOX4:
        output = check_output(["tox", "config"], text=True)
        original_config = ConfigParser()
        original_config.read_string(output)
        config: dict[str, dict[str, Any]] = {}

        for name, section in original_config.items():
            if name == "DEFAULT":
                continue

            config[name] = dict(section)
            # Convert set_env from string to dict
            set_env = {}
            for var in section.get("set_env", "").strip().splitlines():
                k, v = var.split("=")
                if k not in (
                    "PYTHONHASHSEED",
                    "PIP_DISABLE_PIP_VERSION_CHECK",
                    "PYTHONIOENCODING",
                ):
                    set_env[k] = v

            config[name]["set_env"] = set_env

            config[name]["commands"] = [
                wrapjoin(c.split()) for c in section["commands"].strip().splitlines()
            ]

            config[name]["deps"] = wrapjoin(section["deps"].strip().splitlines())

            for option in "skip_install", "use_develop":
                if section.get(option):
                    if section[option] == "False":
                        config[name][option] = False
                    else:
                        config[name][option] = True

            if os.path.isabs(section["base_python"]) or re.match(
                r"py\d+", section["base_python"]
            ):
                impl = (
                    "python" if section["py_impl"] == "cpython" else section["py_impl"]
                )
                config[name]["base_python"] = impl + section["py_dot_ver"]

            change_dir = Path(section.get("change_dir"))
            rel_to_cwd = change_dir.relative_to(Path.cwd())
            if str(rel_to_cwd) == ".":
                config[name]["change_dir"] = None
            else:
                config[name]["change_dir"] = rel_to_cwd

    else:
        config = tox.config.parseconfig([])

    output = _TEMPLATE.render(config=config, wrapjoin=wrapjoin, fixname=fixname)

    write_output_to_file(output, args.output)
