from __future__ import annotations

import dataclasses
import importlib.metadata
import importlib.util
import os
import shutil
import subprocess
import sys
import typing
from types import SimpleNamespace

import packaging.requirements
import packaging.version
import pytest

import nox._cli
import nox.virtualenv

if typing.TYPE_CHECKING:
    from pathlib import Path


def test_get_dependencies() -> None:
    if importlib.util.find_spec("tox") is None:
        with pytest.raises(ModuleNotFoundError):
            list(
                nox._cli.get_dependencies(
                    packaging.requirements.Requirement("nox[tox-to-nox]")
                )
            )
    else:
        deps = nox._cli.get_dependencies(
            packaging.requirements.Requirement("nox[tox-to-nox]")
        )
        dep_list = {
            "argcomplete",
            "attrs",
            "colorlog",
            "dependency-groups",
            "humanize",
            "jinja2",
            "nox",
            "packaging",
            "tox",
            "virtualenv",
        }
        if sys.version_info < (3, 11):
            dep_list.add("tomli")
        assert {d.name for d in deps} == dep_list


def test_version_check() -> None:
    current_version = packaging.version.Version(importlib.metadata.version("nox"))

    assert nox._cli.check_dependencies([f"nox>={current_version}"])
    assert not nox._cli.check_dependencies([f"nox>{current_version}"])

    plus_one = packaging.version.Version(
        f"{current_version.major}.{current_version.minor}.{current_version.micro + 1}"
    )
    assert not nox._cli.check_dependencies([f"nox>={plus_one}"])


def test_nox_check() -> None:
    with pytest.raises(ValueError, match="Must have a nox"):
        nox._cli.check_dependencies(["packaging"])

    with pytest.raises(ValueError, match="Must have a nox"):
        nox._cli.check_dependencies([])


def test_unmatched_specifier() -> None:
    assert not nox._cli.check_dependencies(["packaging<1", "nox"])


def test_invalid_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOX_SCRIPT_MODE", "invalid")
    monkeypatch.setattr(sys, "argv", ["nox"])

    with pytest.raises(SystemExit, match="Invalid NOX_SCRIPT_MODE"):
        nox._cli.main()


def test_invalid_backend_envvar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("NOX_SCRIPT_VENV_BACKEND", "invalid")
    monkeypatch.setattr(sys, "argv", ["nox"])
    # This will return pytest's filename instead, so patching it to None
    monkeypatch.setattr(nox._cli, "get_main_filename", lambda: None)
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath("noxfile.py").write_text(
        "# /// script\n# dependencies=['nox', 'invalid']\n# ///",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Expected venv_backend one of"):
        nox._cli.main()


def test_invalid_backend_inline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "argv", ["nox"])
    # This will return pytest's filename instead, so patching it to None
    monkeypatch.setattr(nox._cli, "get_main_filename", lambda: None)
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath("noxfile.py").write_text(
        "# /// script\n# dependencies=['nox', 'invalid']\n# tool.nox.script-venv-backend = 'invalid'\n# ///",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Expected venv_backend one of"):
        nox._cli.main()


@dataclasses.dataclass
class FakeDistribution:
    origin: SimpleNamespace | None


def test_url_dependency() -> None:
    assert nox._cli.check_url_dependency(
        "https://github.com/a/package",
        FakeDistribution(origin=SimpleNamespace(url="https://github.com/a/package")),  # type: ignore[arg-type]
    )
    assert not nox._cli.check_url_dependency(
        "https://github.com/a/package",
        FakeDistribution(origin=None),  # type: ignore[arg-type]
    )
    assert nox._cli.check_url_dependency(
        "https://github.com/a/package@v1.2.3",
        FakeDistribution(  # type: ignore[arg-type]
            origin=SimpleNamespace(
                url="https://github.com/a/package", requested_revision="v1.2.3"
            )
        ),
    )


def test_dependencies_with_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox._cli, "get_dependencies", lambda x: [x])
    monkeypatch.setattr(
        importlib.metadata,
        "distribution",
        lambda _: FakeDistribution(
            SimpleNamespace(
                url="https://github.com/wntrblm/nox", requested_revision="2024.10.09"
            )
        ),
    )

    assert nox._cli.check_dependencies(
        ["nox @ git+https://github.com/wntrblm/nox@2024.10.09"]
    )
    assert not nox._cli.check_dependencies(
        ["nox @ git+https://github.com/wntrblm/nox@2024.10.10"]
    )
    assert not nox._cli.check_dependencies(
        ["nox @ git+https://github.com/other/nox@2024.10.09"]
    )


@pytest.mark.parametrize("backend", ["uv", "virtualenv"])
def test_run_script_mode_pip_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, backend: str
) -> None:
    """pip must be resolved against the venv's PATH (Windows searches the parent's)."""
    calls: list[list[str]] = []

    fake_venv = SimpleNamespace(
        venv_backend=backend,
        create=lambda: None,
        _get_env=lambda _env: {"PATH": "/fake/venv/bin"},
    )
    monkeypatch.setattr(
        nox.virtualenv, "get_virtualenv", lambda *_args, **_kwargs: fake_venv
    )

    def fake_run(cmd: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda cmd, path=None: f"{path}/{cmd}")

    def fake_execle(_path: str, *_args: object) -> typing.NoReturn:
        raise SystemExit(0)

    monkeypatch.setattr(os, "execle", fake_execle)
    monkeypatch.setattr(sys, "argv", ["nox"])

    with pytest.raises(SystemExit):
        nox._cli.run_script_mode(
            "noxfile.py",
            tmp_path,
            reuse=False,
            dependencies=["nox", "cowsay"],
            venv_backend=backend,
            download_python="never",
        )

    expected = (
        [nox.virtualenv.UV, "pip", "install"]
        if backend == "uv"
        else ["/fake/venv/bin/pip", "install"]
    )
    assert calls[0] == [*expected, "nox", "cowsay"]


@pytest.mark.parametrize(
    ("script_env", "global_env", "toml_value", "cli_args", "expected"),
    [
        ("always", "never", "never", ["--download-python", "never"], "always"),
        (None, None, "always", ["--download-python", "never"], "always"),
        (None, None, None, ["--download-python", "never"], "never"),
        (None, "always", None, [], "always"),
        (None, None, None, [], "auto"),
    ],
)
def test_script_mode_download_python_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    script_env: str | None,
    global_env: str | None,
    toml_value: str | None,
    cli_args: list[str],
    expected: str,
) -> None:
    for var, value in (
        ("NOX_SCRIPT_DOWNLOAD_PYTHON", script_env),
        ("NOX_DOWNLOAD_PYTHON", global_env),
    ):
        if value is None:
            monkeypatch.delenv(var, raising=False)
        else:
            monkeypatch.setenv(var, value)
    monkeypatch.delenv("NOX_SCRIPT_MODE", raising=False)
    monkeypatch.delenv("NOX_SCRIPT_VENV_BACKEND", raising=False)
    monkeypatch.setattr(sys, "argv", ["nox", *cli_args])
    # This will return pytest's filename instead, so patching it to None
    monkeypatch.setattr(nox._cli, "get_main_filename", lambda: None)
    monkeypatch.setattr(nox._cli, "check_dependencies", lambda _deps: False)

    captured: dict[str, object] = {}

    def fake_run_script_mode(*_args: object, **kwargs: object) -> typing.NoReturn:
        captured.update(kwargs)
        raise SystemExit(0)

    monkeypatch.setattr(nox._cli, "run_script_mode", fake_run_script_mode)
    monkeypatch.chdir(tmp_path)
    toml_line = (
        f"# tool.nox.script-download-python = '{toml_value}'\n" if toml_value else ""
    )
    tmp_path.joinpath("noxfile.py").write_text(
        f"# /// script\n# dependencies=['nox']\n{toml_line}# ///",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        nox._cli.main()

    assert captured["download_python"] == expected


def test_dependencies_with_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox._cli, "get_dependencies", lambda x: [x])
    monkeypatch.setattr(
        importlib.metadata, "version", lambda x: {"nox": "2024.10.09", "uv": "0.4.5"}[x]
    )

    assert nox._cli.check_dependencies(["nox", "uv"])
    assert nox._cli.check_dependencies(["nox==2024.10.09", "uv>=0.4"])
    assert nox._cli.check_dependencies(["nox<=2025", "uv~=0.4.2"])
    assert not nox._cli.check_dependencies(["nox==2024.10.10", "uv"])
