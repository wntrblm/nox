from __future__ import annotations

import dataclasses
import importlib.metadata
import importlib.util
import sys
import typing
from types import SimpleNamespace

import packaging.requirements
import packaging.version
import pytest

import nox._cli

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
        if sys.version_info < (3, 9):
            dep_list.add("importlib-resources")
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


def test_dependencies_with_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox._cli, "get_dependencies", lambda x: [x])
    monkeypatch.setattr(
        importlib.metadata, "version", lambda x: {"nox": "2024.10.09", "uv": "0.4.5"}[x]
    )

    assert nox._cli.check_dependencies(["nox", "uv"])
    assert nox._cli.check_dependencies(["nox==2024.10.09", "uv>=0.4"])
    assert nox._cli.check_dependencies(["nox<=2025", "uv~=0.4.2"])
    assert not nox._cli.check_dependencies(["nox==2024.10.10", "uv"])
