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
import shutil
import subprocess
from pathlib import Path
from string import Template
from typing import Any, Callable

import pytest

HAS_CONDA = shutil.which("conda") is not None


@pytest.fixture(autouse=True)
def reset_color_envvars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove color-related envvars to fix test output"""
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)


@pytest.fixture(autouse=True)
def clear_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear the cache for each test."""
    monkeypatch.setattr("nox.registry._REGISTRY", {})


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
            for opt in option_mapping:
                # "uncomment" options with values provided
                text = re.sub(rf"(# )?nox.options.{opt}", f"nox.options.{opt}", text)
            text = Template(text).safe_substitute(**option_mapping)
        path = tmp_path / "noxfile.py"
        path.write_text(text, encoding="utf8")
        return str(path)

    return generate_noxfile


# This fixture will be automatically used unless the test has the 'conda' marker
@pytest.fixture
def prevent_conda(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked_popen(*args: Any, **kwargs: Any) -> Any:
        cmd = args[0][0] if isinstance(args[0], list) else args[0]
        msg = "Use of 'conda' command is blocked in tests without @pytest.mark.conda"
        if "conda" in cmd or "mamba" in cmd:
            raise RuntimeError(msg)
        return original_popen(*args, **kwargs)

    original_popen = subprocess.Popen
    monkeypatch.setattr(subprocess, "Popen", blocked_popen)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "make_conda" in getattr(item, "fixturenames", ()):
            item.add_marker("conda")
        if "conda" in item.keywords:
            item.add_marker(
                pytest.mark.skipif(not HAS_CONDA, reason="Missing conda command.")
            )


# Protection to make sure every conda-using test requests it
def pytest_runtest_setup(item: pytest.Item) -> None:
    if not any(mark.name == "conda" for mark in item.iter_markers()):
        item.add_marker(pytest.mark.usefixtures("prevent_conda"))
