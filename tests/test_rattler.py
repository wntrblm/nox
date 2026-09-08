# Copyright 2026 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""End-to-end tests for the rattler backend. These need py-rattler and network."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

import nox.virtualenv

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("rattler")

pytestmark = pytest.mark.rattler


def test_rattler_create_and_install(tmp_path: Path) -> None:
    location = tmp_path / "renv"
    venv = nox.virtualenv.RattlerEnv(str(location), interpreter="3.12")
    assert venv.create()
    assert (location / "conda-meta").is_dir()

    python = shutil.which("python", path=os.pathsep.join(venv.bin_paths))
    assert python
    out = subprocess.run(
        [python, "-c", "import sys, pip; print(sys.version_info[:2])"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert out.strip() == "(3, 12)"

    # A second install keeps the earlier requested specs (pip, python).
    venv.install("six")
    subprocess.run(
        [python, "-c", "import pip, six"],
        check=True,
    )
    assert any(p.name.startswith("pip-") for p in (location / "conda-meta").iterdir())

    # Reuse detects the existing environment.
    venv = nox.virtualenv.RattlerEnv(str(location), reuse_existing=True)
    assert not venv.create()
    assert venv._reused
