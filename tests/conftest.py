# Copyright 2023 Alethea Katherine Flowers
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

import re
from pathlib import Path
from string import Template
from typing import Callable

import pytest


@pytest.fixture(autouse=True)
def reset_color_envvars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove color-related envvars to fix test output"""
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)


RESOURCES = Path(__file__).parent.joinpath("resources")


@pytest.fixture
def generate_noxfile_options(tmp_path: Path) -> Callable[..., str]:
    """Generate noxfile.py with test and templated options.

    The options are enabled (if disabled) and the values are applied
    if a matching format string is encountered with the option name.
    """

    def generate_noxfile(**option_mapping: str | bool) -> str:
        path = Path(RESOURCES) / "noxfile_options.py"
        text = path.read_text(encoding="utf8")
        if option_mapping:
            for opt, _val in option_mapping.items():
                # "uncomment" options with values provided
                text = re.sub(rf"(# )?nox.options.{opt}", f"nox.options.{opt}", text)
            text = Template(text).safe_substitute(**option_mapping)
        path = tmp_path / "noxfile.py"
        path.write_text(text)
        return str(path)

    return generate_noxfile
