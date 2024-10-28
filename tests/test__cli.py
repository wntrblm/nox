import importlib.metadata
import importlib.util
import sys

import packaging.requirements
import packaging.version
import pytest

import nox._cli


def test_get_dependencies() -> None:
    if importlib.util.find_spec("tox") is None:
        with pytest.raises(ModuleNotFoundError):
            list(
                nox._cli.get_dependencies(
                    packaging.requirements.Requirement("nox[tox_to_nox]")
                )
            )
    else:
        deps = nox._cli.get_dependencies(
            packaging.requirements.Requirement("nox[tox_to_nox]")
        )
        dep_list = {
            "argcomplete",
            "attrs",
            "colorlog",
            "dependency-groups",
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
