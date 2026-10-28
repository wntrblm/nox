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

import nox._rattler
import nox.virtualenv

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from typing import Any

rattler = pytest.importorskip("rattler")

pytestmark = pytest.mark.rattler


@pytest.fixture
def clear_caches() -> Iterator[None]:
    funcs = (nox._rattler._config, nox._rattler._client, nox._rattler._gateway)
    for func in funcs:
        func.cache_clear()
    yield
    for func in funcs:
        func.cache_clear()


def _use_config(monkeypatch: pytest.MonkeyPatch, toml: str) -> None:
    monkeypatch.setattr(
        rattler.Config,
        "load_from_default_locations",
        staticmethod(lambda _tool: rattler.Config.from_toml(toml)),
    )


@pytest.mark.usefixtures("clear_caches")
@pytest.mark.parametrize("offline", [False, True])
def test_gateway_uses_config(monkeypatch: pytest.MonkeyPatch, *, offline: bool) -> None:
    _use_config(
        monkeypatch,
        """
        [repodata-config]
        disable-sharded = true
        [repodata-config."https://example.com/"]
        disable-zstd = true
        """,
    )
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(rattler, "Gateway", lambda **kwargs: calls.append(kwargs))

    nox._rattler._gateway(offline=offline)

    (kwargs,) = calls
    cache_action = "use-cache-only" if offline else "cache-or-fetch"
    assert kwargs["client"] is nox._rattler._client()
    assert kwargs["default_config"] == rattler.SourceConfig(
        sharded_enabled=False, cache_action=cache_action
    )
    assert kwargs["per_channel_config"] == {
        "https://example.com/": rattler.SourceConfig(
            zstd_enabled=False, sharded_enabled=False, cache_action=cache_action
        )
    }


@pytest.mark.usefixtures("clear_caches")
def test_install_never_runs_link_scripts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_config(monkeypatch, 'run-post-link-scripts = "insecure"')
    calls: list[dict[str, Any]] = []

    async def solve(*_args: object, **_kwargs: object) -> list[object]:
        return []

    async def install(*_args: object, **kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(rattler, "solve", solve)
    monkeypatch.setattr(rattler, "install", install)

    nox._rattler.sync(str(tmp_path), ["python"], ["conda-forge"])

    (kwargs,) = calls
    assert kwargs["execute_link_scripts"] is False
    assert kwargs["client"] is nox._rattler._client()


@pytest.mark.usefixtures("clear_caches")
def test_invalid_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('tls-no-verify = "x"\n', encoding="utf-8")
    monkeypatch.setattr(
        rattler.Config,
        "load_from_default_locations",
        staticmethod(lambda _tool: rattler.Config.load_from_files([config])),
    )

    with pytest.raises(RuntimeError, match="rattler config") as excinfo:
        nox._rattler._config()
    assert "tls-no-verify" in str(excinfo.value)


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

    # A new pin replaces the earlier one instead of conflicting with it.
    venv.install("six==1.16.0")
    venv.install("six==1.17.0")
    out = subprocess.run(
        [python, "-c", "import six; print(six.__version__)"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert out.strip() == "1.17.0"

    # Both constraints from one call reach the solver.
    venv.install("six<1.17.0", "six>=1.16.0")
    out = subprocess.run(
        [python, "-c", "import six; print(six.__version__)"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert out.strip() == "1.16.0"

    # Reuse detects the existing environment.
    venv = nox.virtualenv.RattlerEnv(str(location), reuse_existing=True)
    assert not venv.create()
    assert venv._reused
