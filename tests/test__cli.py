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
import python_discovery

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
            "platformdirs",
            "python-discovery",
            "tox",
            "virtualenv",
        }
        if sys.version_info < (3, 11):
            dep_list.add("tomli")
        assert {d.name for d in deps} == dep_list


def test_get_dependencies_memoized(monkeypatch: pytest.MonkeyPatch) -> None:
    requires: dict[str, list[str]] = {
        "a": ['b[x]; extra == "y"', 'c; extra == "y"'],
        "b": ['c; extra == "x"', 'a[y]; extra == "x"'],  # cycle back to a
        "c": [],
    }
    metadata_reads: list[str] = []

    @dataclasses.dataclass
    class FakeMetadataMessage:
        name: str

        def get_all(self, key: str) -> list[str] | None:
            assert key == "requires-dist"
            return requires[self.name] or None

    def fake_metadata(name: str) -> FakeMetadataMessage:
        metadata_reads.append(name)
        return FakeMetadataMessage(name)

    monkeypatch.setattr(importlib.metadata, "metadata", fake_metadata)

    deps = list(nox._cli.get_dependencies(packaging.requirements.Requirement("a[y]")))

    # Every encountered requirement is still yielded (so all specifiers get
    # checked), but each package's metadata is read at most once, and the
    # dependency cycle terminates.
    assert [d.name for d in deps] == ["a", "b", "c", "a", "c"]
    assert metadata_reads == ["a", "b", "c"]


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


def test_check_requires_python() -> None:
    assert nox._cli.check_requires_python(None, "3.12.1")
    assert nox._cli.check_requires_python("", "3.12.1")
    assert nox._cli.check_requires_python(">=3.9", "3.12.1")
    assert nox._cli.check_requires_python(">=3.9,<4", "3.12.1")
    assert not nox._cli.check_requires_python(">=3.13", "3.12.1")
    assert not nox._cli.check_requires_python("<3.10", "3.12.1")
    # A prerelease interpreter satisfies plain specs, but PEP 440 ordering
    # applies: a beta predates its final release.
    assert nox._cli.check_requires_python(">=3.9", "3.15.0b3")
    assert not nox._cli.check_requires_python(">=3.15", "3.15.0b3")
    assert nox._cli.check_requires_python(">=3.15.0b1", "3.15.0b3")


def test_check_requires_python_invalid() -> None:
    with pytest.raises(SystemExit, match="requires-python"):
        nox._cli.check_requires_python("3.12", "3.12.1")


@pytest.mark.parametrize(
    ("version_info", "expected"),
    [
        ((3, 14, 0, "final", 0), "3.14.0"),
        ((3, 14, 0, "beta", 1), "3.14.0b1"),
        ((3, 14, 0, "candidate", 2), "3.14.0rc2"),
        ((3, 14, 0, "alpha", 3), "3.14.0a3"),
    ],
)
def test_format_python_version(
    version_info: tuple[int, int, int, str, int],
    expected: str,
) -> None:
    assert nox._cli._format_python_version(version_info) == expected


def test_venv_python_version(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_venv = SimpleNamespace(_get_env=lambda _env: {"PATH": "/fake/venv/bin"})

    monkeypatch.setattr(shutil, "which", lambda _cmd, **_kwargs: sys.executable)
    version = nox._cli._venv_python_version(fake_venv)  # type: ignore[arg-type]
    assert version == nox._cli._format_python_version(sys.version_info[:5])

    monkeypatch.setattr(shutil, "which", lambda _cmd, **_kwargs: None)
    assert nox._cli._venv_python_version(fake_venv) is None  # type: ignore[arg-type]

    monkeypatch.setattr(shutil, "which", lambda _cmd, **_kwargs: sys.executable)
    monkeypatch.setattr(
        python_discovery.PythonInfo, "from_exe", lambda *_args, **_kwargs: None
    )
    assert nox._cli._venv_python_version(fake_venv) is None  # type: ignore[arg-type]


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


def make_fake_script_venv(**overrides: object) -> SimpleNamespace:
    """A stand-in for the venv run_script_mode builds."""
    venv = SimpleNamespace(
        venv_backend="uv",
        is_sandboxed=True,
        _reused=False,
        create=lambda: None,
        _get_env=lambda _env: {"PATH": "/fake/venv/bin"},
    )
    venv.__dict__.update(overrides)
    return venv


@pytest.fixture
def script_mode_exec(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Stub the install/exec plumbing at the end of run_script_mode.

    Returns the list of commands passed to subprocess.run.
    """
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0)

    def fake_execle(_path: str, *_args: object) -> typing.NoReturn:
        raise SystemExit(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda cmd, path=None: f"{path}/{cmd}")
    monkeypatch.setattr(os, "execle", fake_execle)
    monkeypatch.setattr(sys, "argv", ["nox"])
    return calls


def run_main_with_script(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    toml: str,
    *,
    deps_ok: bool = True,
    argv: list[str] | None = None,
) -> tuple[dict[str, object], pytest.ExceptionInfo[SystemExit]]:
    """Run main() against a script-block noxfile written in tmp_path.

    Returns the kwargs run_script_mode received (empty if it never triggered)
    and the resulting SystemExit.
    """
    monkeypatch.delenv("NOX_SCRIPT_MODE", raising=False)
    monkeypatch.setattr(sys, "argv", ["nox", *(argv or [])])
    # This will return pytest's filename instead, so patching it to None
    monkeypatch.setattr(nox._cli, "get_main_filename", lambda: None)
    monkeypatch.setattr(nox._cli, "check_dependencies", lambda _deps: deps_ok)
    monkeypatch.setattr(nox._cli, "execute_workflow", lambda _args: 0)

    captured: dict[str, object] = {}

    def fake_run_script_mode(*_args: object, **kwargs: object) -> typing.NoReturn:
        captured.update(kwargs)
        raise SystemExit(0)

    monkeypatch.setattr(nox._cli, "run_script_mode", fake_run_script_mode)
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath("noxfile.py").write_text(
        f"# /// script\n{toml}# ///", encoding="utf-8"
    )

    with pytest.raises(SystemExit) as excinfo:
        nox._cli.main()

    return captured, excinfo


@pytest.mark.parametrize("backend", ["uv", "virtualenv"])
def test_run_script_mode_pip_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    backend: str,
    script_mode_exec: list[list[str]],
) -> None:
    """pip must be resolved against the venv's PATH (Windows searches the parent's)."""
    calls = script_mode_exec
    fake_venv = make_fake_script_venv(venv_backend=backend)
    monkeypatch.setattr(
        nox.virtualenv, "get_virtualenv", lambda *_args, **_kwargs: fake_venv
    )

    with pytest.raises(SystemExit):
        nox._cli.run_script_mode(
            "noxfile.py",
            tmp_path,
            reuse=False,
            dependencies=["nox", "cowsay"],
            venv_backend=backend,
            download_python="never",
            requires_python=None,
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
    monkeypatch.delenv("NOX_SCRIPT_VENV_BACKEND", raising=False)
    toml_line = (
        f"# tool.nox.script-download-python = '{toml_value}'\n" if toml_value else ""
    )
    captured, _ = run_main_with_script(
        monkeypatch,
        tmp_path,
        f"# dependencies=['nox']\n{toml_line}",
        deps_ok=False,
        argv=cli_args,
    )
    assert captured["download_python"] == expected


@pytest.mark.parametrize(
    ("toml", "expected"),
    [
        pytest.param(
            '# requires-python = ">=4.0"\n# dependencies=["nox"]\n',
            {"requires_python": ">=4.0", "dependencies": ["nox"]},
            id="mismatch",
        ),
        pytest.param(
            '# requires-python = ">=3.9"\n# dependencies=["nox"]\n',
            None,
            id="satisfied",
        ),
        pytest.param(
            '# requires-python = ">=4.0"\n',
            {"requires_python": ">=4.0", "dependencies": ["nox"]},
            id="implied-nox-dependency",
        ),
    ],
)
def test_script_mode_requires_python(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    toml: str,
    expected: dict[str, object] | None,
) -> None:
    """A failing requires-python triggers script mode; a satisfied one doesn't."""
    captured, excinfo = run_main_with_script(monkeypatch, tmp_path, toml)

    assert excinfo.value.code == 0
    if expected is None:
        assert not captured
    else:
        assert captured["requires_python"] == expected["requires_python"]
        assert captured["dependencies"] == expected["dependencies"]


def test_script_mode_invalid_requires_python(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An invalid spec must error even when the dependency check already failed."""
    captured, excinfo = run_main_with_script(
        monkeypatch,
        tmp_path,
        "# requires-python = \"3.12\"\n# dependencies=['nox']\n",
        deps_ok=False,
    )

    assert 'Invalid "requires-python"' in str(excinfo.value)
    assert not captured, "Must not reach script mode with an invalid spec"


@pytest.mark.usefixtures("script_mode_exec")
def test_run_script_mode_requires_python(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """requires-python is handed to get_virtualenv as the interpreter spec."""
    captured: dict[str, object] = {}

    fake_venv = make_fake_script_venv()

    def fake_get_virtualenv(*_args: object, **kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        return fake_venv

    monkeypatch.setattr(nox.virtualenv, "get_virtualenv", fake_get_virtualenv)

    with pytest.raises(SystemExit):
        nox._cli.run_script_mode(
            "noxfile.py",
            tmp_path,
            reuse=False,
            dependencies=["nox"],
            venv_backend="uv",
            download_python="auto",
            requires_python=">=3.11",
        )

    assert captured["interpreter"] == ">=3.11"


@pytest.mark.parametrize(
    ("env_version", "rebuilds"),
    [("3.9.0", True), (None, True), ("3.12.0", False)],
)
@pytest.mark.usefixtures("script_mode_exec")
def test_run_script_mode_stale_reuse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    env_version: str | None,
    rebuilds: bool,
) -> None:
    """A reused env whose Python fails requires-python must be rebuilt."""
    calls: list[dict[str, object]] = []

    def fake_get_virtualenv(*_args: object, **kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return make_fake_script_venv(_reused=kwargs["reuse_existing"])

    monkeypatch.setattr(nox.virtualenv, "get_virtualenv", fake_get_virtualenv)
    monkeypatch.setattr(nox._cli, "_venv_python_version", lambda _venv: env_version)

    with pytest.raises(SystemExit):
        nox._cli.run_script_mode(
            "noxfile.py",
            tmp_path,
            reuse=True,
            dependencies=["nox"],
            venv_backend="uv",
            download_python="auto",
            requires_python=">=3.10",
        )

    expected = [True, False] if rebuilds else [True]
    assert [c["reuse_existing"] for c in calls] == expected


def test_run_script_mode_interpreter_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_create() -> typing.NoReturn:
        spec = ">=4.0"
        raise nox.virtualenv.InterpreterNotFound(spec)

    fake_venv = make_fake_script_venv(create=fake_create)
    monkeypatch.setattr(
        nox.virtualenv, "get_virtualenv", lambda *_args, **_kwargs: fake_venv
    )

    with pytest.raises(SystemExit, match="requires-python"):
        nox._cli.run_script_mode(
            "noxfile.py",
            tmp_path,
            reuse=False,
            dependencies=["nox"],
            venv_backend="uv",
            download_python="never",
            requires_python=">=4.0",
        )


@pytest.mark.parametrize(
    ("requires_python", "satisfied"),
    [(">=4.0", False), (">=3.9", True)],
    ids=["mismatch", "satisfied"],
)
@pytest.mark.usefixtures("script_mode_exec")
def test_run_script_mode_none_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    requires_python: str,
    satisfied: bool,
) -> None:
    """The "none" backend can't switch interpreters: a mismatch is an error,
    a satisfied spec runs in the current environment."""
    fake_venv = make_fake_script_venv(venv_backend="none", is_sandboxed=False)
    monkeypatch.setattr(
        nox.virtualenv, "get_virtualenv", lambda *_args, **_kwargs: fake_venv
    )

    with pytest.raises(SystemExit) as excinfo:
        nox._cli.run_script_mode(
            "noxfile.py",
            tmp_path,
            reuse=True,
            dependencies=["nox"],
            venv_backend="none",
            download_python="auto",
            requires_python=requires_python,
        )

    if satisfied:
        assert excinfo.value.code == 0
    else:
        assert "requires-python" in str(excinfo.value)


def test_dependencies_with_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox._cli, "get_dependencies", lambda x: [x])
    monkeypatch.setattr(
        importlib.metadata, "version", lambda x: {"nox": "2024.10.09", "uv": "0.4.5"}[x]
    )

    assert nox._cli.check_dependencies(["nox", "uv"])
    assert nox._cli.check_dependencies(["nox==2024.10.09", "uv>=0.4"])
    assert nox._cli.check_dependencies(["nox<=2025", "uv~=0.4.2"])
    assert not nox._cli.check_dependencies(["nox==2024.10.10", "uv"])
