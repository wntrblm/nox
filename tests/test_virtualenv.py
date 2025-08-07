# Copyright 2016 Alethea Katherine Flowers
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

import functools
import os
import re
import shutil
import subprocess
import sys
import types
from importlib import metadata
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, NamedTuple, NoReturn
from unittest import mock

import pytest
from packaging import version

import nox.command
import nox.virtualenv

if TYPE_CHECKING:
    from collections.abc import Callable

    from nox.virtualenv import CondaEnv, ProcessEnv, VirtualEnv

IS_WINDOWS = sys.platform.startswith("win")
HAS_CONDA = shutil.which("conda") is not None
HAS_UV = shutil.which("uv") is not None
RAISE_ERROR = "RAISE_ERROR"
VIRTUALENV_VERSION = metadata.version("virtualenv")

has_uv = pytest.mark.skipif(not HAS_UV, reason="Missing uv command.")
has_conda = pytest.mark.skipif(not HAS_CONDA, reason="Missing conda command.")


class TextProcessResult(NamedTuple):
    stdout: str
    returncode: int = 0


@pytest.fixture
def make_one(
    tmp_path: Path,
) -> Callable[..., tuple[nox.virtualenv.VirtualEnv | nox.virtualenv.ProcessEnv, Path]]:
    def factory(
        *args: Any, venv_backend: str = "virtualenv", **kwargs: Any
    ) -> tuple[nox.virtualenv.VirtualEnv | nox.virtualenv.ProcessEnv, Path]:
        location = tmp_path.joinpath("venv")
        try:
            venv_fn = nox.virtualenv.ALL_VENVS[venv_backend]
        except KeyError:
            venv_fn = functools.partial(
                nox.virtualenv.VirtualEnv, venv_backend=venv_backend
            )
        venv = venv_fn(str(location), *args, **kwargs)
        return (venv, location)

    return factory


@pytest.fixture
def make_conda(tmp_path: Path) -> Callable[..., tuple[CondaEnv, Path]]:
    def factory(*args: Any, **kwargs: Any) -> tuple[CondaEnv, Path]:
        location = tmp_path.joinpath("condaenv")
        venv = nox.virtualenv.CondaEnv(str(location), *args, **kwargs)
        return (venv, location)

    return factory


@pytest.fixture
def patch_sysfind(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[tuple[str, ...], str | None, str], None]:
    """Provides a function to patch ``sysfind`` with parameters for tests related
    to locating a Python interpreter in the system ``PATH``.
    """

    def patcher(
        only_find: tuple[str, ...], sysfind_result: str | None, sysexec_result: str
    ) -> None:
        """Monkeypatches python discovery, causing specific results to be found.

        Args:
            only_find (Tuple[str]): The strings for which ``shutil.which`` should be successful,
                e.g. ``("python", "python.exe")``
            sysfind_result (Optional[str]): The ``path`` string to create the returned
                mocked ``path`` object with which will represent the found Python interpreter,
                or ``None``.
            sysexec_result (str): A string that should be returned when executing the
                mocked ``path`` object. Usually a Python version string.
                Use the global ``RAISE_ERROR`` to have ``sysexec`` fail.
        """

        def special_which(name: str, path: Any = None) -> str | None:  # noqa: ARG001
            if sysfind_result is None:
                return None
            if name.lower() in only_find:
                return sysfind_result or name
            return None

        monkeypatch.setattr(shutil, "which", special_which)

        def special_run(cmd: Any, *args: Any, **kwargs: Any) -> TextProcessResult:  # noqa: ARG001
            return TextProcessResult(sysexec_result)

        monkeypatch.setattr(subprocess, "run", special_run)

    return patcher


def test_process_env_constructor() -> None:
    penv = nox.virtualenv.PassthroughEnv()
    assert not penv.bin_paths
    with pytest.raises(
        ValueError, match=r"^The environment does not have a bin directory\.$"
    ):
        print(penv.bin)

    penv = nox.virtualenv.PassthroughEnv(env={"SIGIL": "123"})
    assert penv.env["SIGIL"] == "123"

    penv = nox.virtualenv.PassthroughEnv(bin_paths=["/bin"])
    assert penv.bin == "/bin"


def test_process_env_create() -> None:
    with pytest.raises(TypeError):
        nox.virtualenv.ProcessEnv()  # type: ignore[abstract]


def test_invalid_venv_create(
    make_one: Callable[
        ..., tuple[nox.virtualenv.VirtualEnv | nox.virtualenv.ProcessEnv, Path]
    ],
) -> None:
    with pytest.raises(ValueError, match="venv_backend 'invalid' not recognized"):
        make_one(venv_backend="invalid")


def test_condaenv_constructor_defaults(
    make_conda: Callable[..., tuple[CondaEnv, Path]],
) -> None:
    venv, _ = make_conda()
    assert venv.location
    assert venv.interpreter is None
    assert venv.reuse_existing is False


def test_condaenv_constructor_explicit(
    make_conda: Callable[..., tuple[CondaEnv, Path]],
) -> None:
    venv, _ = make_conda(interpreter="3.5", reuse_existing=True)
    assert venv.location
    assert venv.interpreter == "3.5"
    assert venv.reuse_existing is True


@has_conda
def test_condaenv_create(make_conda: Callable[..., tuple[CondaEnv, Path]]) -> None:
    venv, dir_ = make_conda()
    venv.create()

    if IS_WINDOWS:
        assert dir_.joinpath("python.exe").exists()
        assert dir_.joinpath("Scripts", "pip.exe").exists()
        assert dir_.joinpath("Library").exists()
    else:
        assert dir_.joinpath("bin", "python").exists()
        assert dir_.joinpath("bin", "pip").exists()
        assert dir_.joinpath("lib").exists()

    # Test running create on an existing environment. It should be deleted.
    dir_.joinpath("test.txt").touch()
    venv.create()
    assert not dir_.joinpath("test.txt").exists()

    # Test running create on an existing environment with reuse_existing
    # enabled, it should not be deleted.
    dir_.joinpath("test.txt").touch()
    assert dir_.joinpath("test.txt").exists()
    venv.reuse_existing = True
    venv.create()
    assert dir_.joinpath("test.txt").exists()
    assert venv._reused


@has_conda
def test_condaenv_create_with_params(
    make_conda: Callable[..., tuple[CondaEnv, Path]],
) -> None:
    venv, dir_ = make_conda(venv_params=["--verbose"])
    venv.create()
    if IS_WINDOWS:
        assert dir_.joinpath("python.exe").exists()
        assert dir_.joinpath("Scripts", "pip.exe").exists()
    else:
        assert dir_.joinpath("bin", "python").exists()
        assert dir_.joinpath("bin", "pip").exists()


@has_conda
def test_condaenv_create_interpreter(
    make_conda: Callable[..., tuple[CondaEnv, Path]],
) -> None:
    venv, dir_ = make_conda(interpreter="3.12")
    venv.create()
    if IS_WINDOWS:
        assert dir_.joinpath("python.exe").exists()
        assert dir_.joinpath("python312.dll").exists()
        assert dir_.joinpath("python312.pdb").exists()
        assert not dir_.joinpath("python312.exe").exists()
    else:
        assert dir_.joinpath("bin", "python").exists()
        assert dir_.joinpath("bin", "python3.12").exists()


@has_conda
def test_conda_env_create_verbose(
    make_conda: Callable[..., tuple[CondaEnv, Path]],
) -> None:
    venv, _dir = make_conda()
    with mock.patch("nox.virtualenv.nox.command.run") as mock_run:
        venv.create()

    _args, kwargs = mock_run.call_args
    assert kwargs["log"] is False

    nox.options.verbose = True
    with mock.patch("nox.virtualenv.nox.command.run") as mock_run:
        venv.create()

    _args, kwargs = mock_run.call_args
    assert kwargs["log"]


@mock.patch("nox.virtualenv._PLATFORM", new="win32")
def test_condaenv_bin_windows(make_conda: Callable[..., tuple[CondaEnv, Path]]) -> None:
    venv, dir_ = make_conda()
    assert [
        str(dir_),
        str(dir_.joinpath("Library", "mingw-w64", "bin")),
        str(dir_.joinpath("Library", "usr", "bin")),
        str(dir_.joinpath("Library", "bin")),
        str(dir_.joinpath("Scripts")),
        str(dir_.joinpath("bin")),
    ] == venv.bin_paths


@has_conda
def test_condaenv_(make_conda: Callable[..., tuple[CondaEnv, Path]]) -> None:
    venv, _dir = make_conda()
    assert not venv.is_offline()


@has_conda
def test_condaenv_detection(make_conda: Callable[..., tuple[CondaEnv, Path]]) -> None:
    venv, dir_ = make_conda()
    venv.create()
    conda = shutil.which("conda")
    assert conda

    env = {k: v for k, v in {**os.environ, **venv.env}.items() if v is not None}

    proc_result = subprocess.run(
        [conda, "list"],
        env=env,
        check=True,
        capture_output=True,
    )
    output = proc_result.stdout.decode()
    path_regex = re.compile(r"packages in environment at (?P<env_dir>.+):")

    output_match = path_regex.search(output)
    assert output_match
    assert dir_.samefile(output_match.group("env_dir"))


@has_uv
def test_uv_creation(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one(venv_backend="uv")
    assert venv.location
    assert venv.interpreter is None
    assert venv.reuse_existing is False
    assert venv.venv_backend == "uv"

    venv.create()
    assert venv._check_reused_environment_type()

    venv.create()
    assert venv._check_reused_environment_type()


@has_uv
def test_uv_managed_python(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    make_one(interpreter="cpython3.12", venv_backend="uv")


def test_constructor_defaults(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one()
    assert venv.location
    assert venv.interpreter is None
    assert venv.reuse_existing is False
    assert venv.venv_backend == "virtualenv"


def test_constructor_pypy_dash(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one(interpreter="pypy-3.10")
    assert venv.location
    assert venv.interpreter == "pypy3.10"
    assert venv.reuse_existing is False
    assert venv.venv_backend == "virtualenv"


@pytest.mark.skipif(IS_WINDOWS, reason="Not testing multiple interpreters on Windows.")
def test_constructor_explicit(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one(interpreter="python3.5", reuse_existing=True)
    assert venv.location
    assert venv.interpreter == "python3.5"
    assert venv.reuse_existing is True


def test_env(
    monkeypatch: pytest.MonkeyPatch,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    monkeypatch.setenv("SIGIL", "123")
    venv, _ = make_one()
    assert len(venv.bin_paths) == 1
    assert venv.bin_paths[0] == venv.bin
    assert venv.bin_paths[0] not in os.environ["PATH"]


def test_blacklisted_env(
    monkeypatch: pytest.MonkeyPatch,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    monkeypatch.setenv("__PYVENV_LAUNCHER__", "meep")
    venv, _ = make_one()
    assert len(venv.bin_paths) == 1
    assert venv.bin_paths[0] == venv.bin
    assert "__PYVENV_LAUNCHER__" not in venv.bin


def test__clean_location(
    monkeypatch: pytest.MonkeyPatch,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, dir_ = make_one()

    # Don't reuse existing, but doesn't currently exist.
    # Should return True indicating that the venv needs to be created.
    monkeypatch.setattr(
        nox.virtualenv.VirtualEnv, "_check_reused_environment_type", mock.MagicMock()
    )
    monkeypatch.setattr(
        nox.virtualenv.VirtualEnv,
        "_check_reused_environment_interpreter",
        mock.MagicMock(),
    )
    monkeypatch.delattr(nox.virtualenv.shutil, "rmtree")  # type: ignore[attr-defined]
    assert not dir_.exists()
    assert venv._clean_location()

    # Reuse existing, and currently exists.
    # Should return False indicating that the venv doesn't need to be created.
    dir_.mkdir()
    assert dir_.exists()
    venv.reuse_existing = True
    assert not venv._clean_location()

    # Don't reuse existing, and currently exists.
    # Should return True indicating the venv needs to be created.
    monkeypatch.undo()
    assert dir_.exists()
    venv.reuse_existing = False
    assert venv._clean_location()
    assert not dir_.exists()

    # Reuse existing, but doesn't exist.
    # Should return True indicating the venv needs to be created.
    venv.reuse_existing = True
    assert venv._clean_location()


def test_bin_paths(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
) -> None:
    venv, dir_ = make_one()

    assert venv.bin_paths
    assert len(venv.bin_paths) == 1
    assert venv.bin_paths[0] == venv.bin

    assert str(dir_.joinpath("Scripts" if IS_WINDOWS else "bin")) == venv.bin


@mock.patch("nox.virtualenv._PLATFORM", new="win32")
def test_bin_windows(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
) -> None:
    venv, dir_ = make_one()
    assert venv.bin_paths
    assert len(venv.bin_paths) == 1
    assert venv.bin_paths[0] == venv.bin
    assert str(dir_.joinpath("Scripts")) == venv.bin


@mock.patch("nox.virtualenv._PLATFORM", new="win32")
@mock.patch("nox.virtualenv._IS_MINGW", new=True)
def test_bin_windows_mingw(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
) -> None:
    venv, dir_ = make_one()
    assert venv.bin_paths
    assert len(venv.bin_paths) == 1
    assert venv.bin_paths[0] == venv.bin
    assert str(dir_.joinpath("bin")) == venv.bin


def test_create(
    monkeypatch: pytest.MonkeyPatch,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    monkeypatch.setenv("CONDA_PREFIX", "no-prefix-allowed")
    monkeypatch.setenv("NOT_CONDA_PREFIX", "something-else")

    venv, dir_ = make_one()
    venv.create()

    assert venv.env["CONDA_PREFIX"] is None
    assert "NOT_CONDA_PREFIX" not in venv.env

    if IS_WINDOWS:
        assert dir_.joinpath("Scripts", "python.exe").exists()
        assert dir_.joinpath("Scripts", "pip.exe").exists()
        assert dir_.joinpath("Lib").exists()
        assert str(dir_.joinpath("Scripts")) in venv.bin_paths
    else:
        assert dir_.joinpath("bin", "python").exists()
        assert dir_.joinpath("bin", "pip").exists()
        assert dir_.joinpath("lib").exists()
        assert str(dir_.joinpath("bin")) in venv.bin_paths

    # Test running create on an existing environment. It should be deleted.
    dir_.joinpath("test.txt").touch()
    venv.create()
    assert not dir_.joinpath("test.txt").exists()

    # Test running create on an existing environment with reuse_existing
    # enabled, it should not be deleted.
    dir_.joinpath("test.txt").touch()
    assert dir_.joinpath("test.txt").exists()
    venv.reuse_existing = True

    venv.create()

    assert venv._reused
    assert dir_.joinpath("test.txt").exists()


def test_create_reuse_environment(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
) -> None:
    venv, _location = make_one(reuse_existing=True)
    venv.create()

    reused = not venv.create()

    assert reused


def test_create_reuse_environment_with_different_interpreter(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Making the reuse requirement more strict
    monkeypatch.setenv("NOX_ENABLE_STALENESS_CHECK", "1")

    venv, location = make_one(reuse_existing=True)
    venv.create()

    # Pretend that the environment was created with a different interpreter.
    monkeypatch.setattr(venv, "_check_reused_environment_interpreter", lambda: False)

    # Create a marker file. It should be gone after the environment is re-created.
    location.joinpath("marker").touch()

    reused = not venv.create()

    assert not reused
    assert not location.joinpath("marker").exists()


@has_uv
def test_create_reuse_stale_venv_environment(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
) -> None:
    venv, location = make_one(reuse_existing=True)
    venv.create()

    # Drop a uv-style pyvenv.cfg into the environment.
    pyvenv_cfg = """\
    home = /usr/bin
    include-system-site-packages = false
    version = 3.9.6
    uv = 0.1.9
    """
    location.joinpath("pyvenv.cfg").write_text(dedent(pyvenv_cfg), encoding="utf-8")

    reused = not venv.create()

    assert not reused


def test_not_stale_virtualenv_environment(
    make_one: Callable[
        ..., tuple[nox.virtualenv.VirtualEnv | nox.virtualenv.ProcessEnv, Path]
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Making the reuse requirement more strict
    monkeypatch.setenv("NOX_ENABLE_STALENESS_CHECK", "1")

    venv, _location = make_one(reuse_existing=True, venv_backend="virtualenv")
    venv.create()

    venv, _location = make_one(reuse_existing=True, venv_backend="virtualenv")
    reused = not venv.create()

    assert reused


@has_conda
def test_stale_virtualenv_to_conda_environment(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
) -> None:
    venv, _location = make_one(reuse_existing=True, venv_backend="virtualenv")
    venv.create()

    venv, _location = make_one(reuse_existing=True, venv_backend="conda")
    reused = not venv.create()

    # The environment is not reused because it is now conda style
    # environment.
    assert not reused


@has_conda
def test_reuse_conda_environment(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
) -> None:
    venv, _ = make_one(reuse_existing=True, venv_backend="conda")
    venv.create()
    assert venv.bin_paths
    assert venv.bin_paths[-1].endswith("bin")

    venv, _ = make_one(reuse_existing=True, venv_backend="conda")
    reused = not venv.create()

    assert reused


# This mocks micromamba so that it doesn't need to be installed.
@has_conda
def test_micromamba_environment(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conda_path = shutil.which("conda")
    which = shutil.which
    monkeypatch.setattr(
        shutil, "which", lambda x: conda_path if x == "micromamba" else which(x)
    )
    venv, _ = make_one(reuse_existing=True, venv_backend="micromamba")
    run = mock.Mock()
    monkeypatch.setattr(nox.command, "run", run)
    venv.create()
    run.assert_called_once()
    (args,) = run.call_args.args
    assert args[0] == "micromamba"
    assert "--channel=conda-forge" in args


# This mocks micromamba so that it doesn't need to be installed.
@pytest.mark.parametrize(
    "params",
    [["--channel=default"], ["-cdefault"], ["-c", "default"], ["--channel", "default"]],
)
@has_conda
def test_micromamba_channel_environment(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
    monkeypatch: pytest.MonkeyPatch,
    params: list[str],
) -> None:
    conda_path = shutil.which("conda")
    which = shutil.which
    monkeypatch.setattr(
        shutil, "which", lambda x: conda_path if x == "micromamba" else which(x)
    )
    venv, _ = make_one(reuse_existing=True, venv_backend="micromamba")
    run = mock.Mock()
    monkeypatch.setattr(nox.command, "run", run)
    venv.venv_params = params
    venv.create()
    run.assert_called_once()
    (args,) = run.call_args.args
    assert args[0] == "micromamba"
    for p in params:
        assert p in args
    assert "--channel=conda-forge" not in args


@pytest.mark.parametrize(
    ("frm", "to", "result"),
    [
        ("virtualenv", "venv", True),
        ("venv", "virtualenv", True),
        ("virtualenv", "uv", True),
        pytest.param("uv", "virtualenv", False, marks=has_uv),
        pytest.param("conda", "virtualenv", False, marks=has_conda),
    ],
)
def test_stale_environment(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
    frm: str,
    to: str,
    result: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOX_ENABLE_STALENESS_CHECK", "1")
    venv, _ = make_one(reuse_existing=True, venv_backend=frm)
    venv.create()
    assert venv.venv_backend == frm

    venv, _ = make_one(reuse_existing=True, venv_backend=to)
    reused = venv._check_reused_environment_type()
    assert venv.venv_backend == to

    assert reused == result


def test_passthrough_environment_venv_backend(
    make_one: Callable[..., tuple[ProcessEnv, Path]],
) -> None:
    venv, _ = make_one(venv_backend="none")
    venv.create()
    assert venv.venv_backend == "none"


@has_uv
def test_create_reuse_stale_virtualenv_environment(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOX_ENABLE_STALENESS_CHECK", "1")
    venv, location = make_one(reuse_existing=True, venv_backend="venv")
    venv.create()

    # Drop a uv-style pyvenv.cfg into the environment.
    pyvenv_cfg = """\
    home = /usr
    implementation = CPython
    version_info = 3.9.6.final.0
    uv = 0.1.9
    include-system-site-packages = false
    base-prefix = /usr
    base-exec-prefix = /usr
    base-executable = /usr/bin/python3.9
    """
    location.joinpath("pyvenv.cfg").write_text(dedent(pyvenv_cfg), encoding="utf-8")

    reused = not venv.create()

    # The environment is not reused because it does not look like a
    # venv-style environment.
    assert not reused


@has_uv
def test_create_reuse_uv_environment(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
) -> None:
    venv, location = make_one(reuse_existing=True, venv_backend="uv")
    venv.create()

    # Place a spurious occurrence of "uv" in the pyvenv.cfg.
    pyvenv_cfg = location.joinpath("pyvenv.cfg")
    pyvenv_cfg.write_text(
        pyvenv_cfg.read_text(encoding="utf-8") + "bogus = uv\n", encoding="utf-8"
    )

    reused = not venv.create()

    # The environment is reused because it looks like a uv environment
    assert reused


UV_IN_PIPX_VENV = "/home/user/.local/pipx/venvs/nox/bin/uv"


@pytest.mark.parametrize(
    (
        "uv_env",
        "which_result",
        "find_uv_bin_result",
        "found",
        "path",
        "vers",
        "vers_rc",
    ),
    [
        pytest.param(
            None,
            "/usr/bin/uv",
            UV_IN_PIPX_VENV,
            True,
            UV_IN_PIPX_VENV,
            "0.5.0",
            0,
            id="pkg_pipx_uv_0.5",
        ),
        pytest.param(
            None,
            "/usr/bin/uv",
            UV_IN_PIPX_VENV,
            True,
            UV_IN_PIPX_VENV,
            "0.6.0",
            0,
            id="pkg_pipx_uv_0.6",
        ),
        pytest.param(
            "custom",
            "/usr/bin/uv",
            UV_IN_PIPX_VENV,
            True,
            "custom",
            "0.6.0",
            0,
            id="UV_pkg_pipx_uv_0.6",
        ),
        pytest.param(
            None,
            "/usr/bin/uv",
            UV_IN_PIPX_VENV,
            True,
            UV_IN_PIPX_VENV,
            "0.7.0",
            0,
            id="pkg_pipx_uv_0.7",
        ),
        pytest.param(
            "custom",
            "/usr/bin/uv",
            UV_IN_PIPX_VENV,
            True,
            "custom",
            "0.7.0",
            0,
            id="UV_pkg_pipx_uv_0.7",
        ),
        pytest.param(
            None,
            "/usr/bin/uv",
            UV_IN_PIPX_VENV,
            False,
            "uv",
            "0.0.0",
            0,
            id="pkg_system_uv_0.0",
        ),
        pytest.param(
            None,
            "/usr/bin/uv",
            UV_IN_PIPX_VENV,
            False,
            "uv",
            "0.6.0",
            1,
            id="pkg_system_uv_0.6_broken",
        ),
        pytest.param(
            None,
            "/usr/bin/uv",
            UV_IN_PIPX_VENV,
            False,
            "uv",
            "0.7.0",
            1,
            id="pkg_system_uv_0.7_broken",
        ),
        pytest.param(
            None, "/usr/bin/uv", None, True, "uv", "0.7.0", 0, id="system_uv_0.7"
        ),
        pytest.param(
            None, "/usr/bin/uv", None, True, "uv", "0.6.0", 0, id="system_uv_0.6"
        ),
        pytest.param(
            None, "/usr/bin/uv", None, False, "uv", "0.0.0", 0, id="system_uv_0.0"
        ),
        pytest.param(
            None,
            "/usr/bin/uv",
            None,
            False,
            "uv",
            "0.6.0",
            1,
            id="system_uv_0.6_broken",
        ),
        pytest.param(
            None,
            "/usr/bin/uv",
            None,
            False,
            "uv",
            "0.7.0",
            1,
            id="system_uv_0.7_broken",
        ),
        pytest.param(
            None,
            None,
            UV_IN_PIPX_VENV,
            True,
            UV_IN_PIPX_VENV,
            "0.5.0",
            0,
            id="pipx_uv_0.5",
        ),
        pytest.param(
            None,
            None,
            UV_IN_PIPX_VENV,
            True,
            UV_IN_PIPX_VENV,
            "0.7.0",
            0,
            id="pipx_uv_0.7",
        ),
        pytest.param(None, None, None, False, "uv", "0.5.0", 0, id="no_uv_0.5"),
    ],
)
def test_find_uv(
    monkeypatch: pytest.MonkeyPatch,
    uv_env: str | None,
    which_result: str | None,
    find_uv_bin_result: str | None,
    found: bool,
    path: str,
    vers: str,
    vers_rc: int,
) -> None:
    monkeypatch.delenv("UV", raising=False)
    if uv_env:
        monkeypatch.setenv("UV", uv_env)

    def find_uv_bin() -> str:
        if find_uv_bin_result:
            return find_uv_bin_result
        raise FileNotFoundError()

    def mock_run(*args: Any, **kwargs: object) -> subprocess.CompletedProcess[str]:
        if version.Version(vers) < version.Version("0.7.0") and "self" in args[0]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=2,
            )
        return subprocess.CompletedProcess(
            args=args[0],
            stdout=f'{{"version": "{vers}", "commit_info": null}}',
            returncode=vers_rc,
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    monkeypatch.setattr(
        shutil, "which", lambda x: which_result if x.endswith("uv") else uv_env
    )
    monkeypatch.setattr(Path, "samefile", lambda a, b: a == b)
    monkeypatch.setitem(
        sys.modules, "uv", types.SimpleNamespace(find_uv_bin=find_uv_bin)
    )

    assert nox.virtualenv.find_uv() == (
        found,
        path,
        version.Version(vers if vers_rc == 0 else "0"),
    )


@pytest.mark.parametrize(
    ("return_code", "stdout", "expected_result"),
    [
        (0, '{"version": "0.2.3", "commit_info": null}', "0.2.3"),
        (1, None, "0.0"),
        (1, '{"version": "9.9.9", "commit_info": null}', "0.0"),
    ],
)
def test_uv_version(
    monkeypatch: pytest.MonkeyPatch,
    return_code: int,
    stdout: str | None,
    expected_result: str,
) -> None:
    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["uv", "self", "version", "--output-format", "json"],
            stdout=stdout,
            returncode=return_code,
        )

    monkeypatch.setattr(subprocess, "run", mock_run)
    assert nox.virtualenv.uv_version(nox.virtualenv.UV) == version.Version(
        expected_result
    )


def test_uv_version_no_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_exception(*args: object, **kwargs: object) -> NoReturn:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", mock_exception)
    assert nox.virtualenv.uv_version(nox.virtualenv.UV) == version.Version("0.0")


@pytest.mark.parametrize(
    ("requested_python", "expected_result"),
    [
        ("3.11", True),
        ("pypy3.8", True),
        ("cpython3.9", True),
        ("python3.12", True),
        ("nonpython9.22", False),
        ("java11", False),
    ],
)
@has_uv
def test_uv_install(requested_python: str, expected_result: bool) -> None:
    assert nox.virtualenv.uv_install_python(requested_python) == expected_result


def test_create_reuse_venv_environment(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Making the reuse requirement more strict
    monkeypatch.setenv("NOX_ENABLE_STALENESS_CHECK", "1")

    venv, location = make_one(reuse_existing=True, venv_backend="venv")
    venv.create()

    # Place a spurious occurrence of "virtualenv" in the pyvenv.cfg.
    pyvenv_cfg = location.joinpath("pyvenv.cfg")
    pyvenv_cfg.write_text(
        pyvenv_cfg.read_text(encoding="utf-8") + "bogus = virtualenv\n",
        encoding="utf-8",
    )

    reused = not venv.create()

    # The environment should be detected as venv-style and reused.
    assert reused


@pytest.mark.skipif(IS_WINDOWS, reason="Avoid 'No pyvenv.cfg file' error on Windows.")
def test_create_reuse_oldstyle_virtualenv_environment(
    make_one: Callable[..., tuple[VirtualEnv | ProcessEnv, Path]],
) -> None:
    venv, location = make_one(reuse_existing=True)
    venv.create()

    pyvenv_cfg = location.joinpath("pyvenv.cfg")
    if not pyvenv_cfg.exists():
        pytest.skip("Requires virtualenv >= 20.0.0.")

    # virtualenv < 20.0.0 does not create a pyvenv.cfg file.
    pyvenv_cfg.unlink()

    reused = not venv.create()

    # The environment is detected as virtualenv-style and reused.
    assert reused


@pytest.mark.skipif(IS_WINDOWS, reason="Avoid 'No pyvenv.cfg file' error on Windows.")
def test_inner_functions_reusing_venv(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOX_ENABLE_STALENESS_CHECK", "1")
    venv, location = make_one(reuse_existing=True)
    venv.create()

    txt = location.joinpath("pyvenv.cfg").read_text(encoding="utf-8")
    cfg = {
        (v := line.partition("="))[0].strip(): v[-1].strip()
        for line in txt.splitlines()
    }
    home = cfg["home"]

    # Drop a venv-style pyvenv.cfg into the environment.
    pyvenv_cfg = f"""\
    home = {home}
    include-system-site-packages = false
    version = 3.10
    base-prefix = foo
    """
    location.joinpath("pyvenv.cfg").write_text(dedent(pyvenv_cfg), encoding="utf-8")

    config = venv._read_pyvenv_cfg()
    assert config
    base_prefix = config["base-prefix"]
    assert base_prefix == "foo"

    reused_interpreter = venv._check_reused_environment_interpreter()
    # The created won't match 'foo'
    assert not reused_interpreter


@pytest.mark.skipif(
    version.parse(VIRTUALENV_VERSION) >= version.parse("20.22.0"),
    reason="Python 2.7 unsupported for virtualenv>=20.22.0",
)
def test_create_reuse_python2_environment(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _location = make_one(reuse_existing=True, interpreter="2.7")

    try:
        venv.create()
    except nox.virtualenv.InterpreterNotFound:
        pytest.skip("Requires Python 2.7 installation.")

    reused = not venv.create()

    assert reused


def test_create_venv_backend(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _dir = make_one(venv_backend="venv")
    venv.create()


@pytest.mark.skipif(IS_WINDOWS, reason="Not testing multiple interpreters on Windows.")
def test_create_interpreter(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, dir_ = make_one(interpreter="python3")
    venv.create()
    assert dir_.joinpath("bin", "python").exists()
    assert dir_.joinpath("bin", "python3").exists()


def test__resolved_interpreter_none(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    # Establish that the _resolved_interpreter method is a no-op if the
    # interpreter is not set.
    venv, _ = make_one(interpreter=None)
    assert venv._resolved_interpreter == sys.executable


@pytest.mark.parametrize(
    ("input_", "expected"),
    [
        ("3", "python3"),
        ("3.6", "python3.6"),
        ("3.6.2", "python3.6"),
        ("3.10", "python3.10"),
        ("2.7.15", "python2.7"),
    ],
)
@mock.patch("nox.virtualenv._PLATFORM", new="linux")
@mock.patch.object(shutil, "which", return_value=True)
def test__resolved_interpreter_numerical_non_windows(
    which: mock.Mock,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
    input_: str,
    expected: str,
) -> None:
    venv, _ = make_one(interpreter=input_)

    assert venv._resolved_interpreter == expected
    which.assert_called_once_with(expected)


@pytest.mark.parametrize("input_", ["2.", "2.7."])
@mock.patch("nox.virtualenv._PLATFORM", new="linux")
@mock.patch.object(shutil, "which", return_value=False)
def test__resolved_interpreter_invalid_numerical_id(
    which: mock.Mock,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
    input_: str,
) -> None:
    venv, _ = make_one(interpreter=input_)

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        print(venv._resolved_interpreter)

    which.assert_called_once_with(input_)


@mock.patch("nox.virtualenv._PLATFORM", new="linux")
@mock.patch.object(shutil, "which", return_value=False)
def test__resolved_interpreter_32_bit_non_windows(
    which: mock.Mock, make_one: Callable[..., tuple[VirtualEnv, Path]]
) -> None:
    venv, _ = make_one(interpreter="3.6-32")

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        print(venv._resolved_interpreter)
    which.assert_called_once_with("3.6-32")


@mock.patch("nox.virtualenv._PLATFORM", new="linux")
@mock.patch.object(shutil, "which", return_value=True)
def test__resolved_interpreter_non_windows(
    which: mock.Mock, make_one: Callable[..., tuple[VirtualEnv, Path]]
) -> None:
    # Establish that the interpreter is simply passed through resolution
    # on non-Windows.
    venv, _ = make_one(interpreter="python3.6")

    assert venv._resolved_interpreter == "python3.6"
    which.assert_called_once_with("python3.6")


@mock.patch("nox.virtualenv._PLATFORM", new="win32")
@mock.patch.object(shutil, "which")
def test__resolved_interpreter_windows_full_path(
    which: mock.Mock, make_one: Callable[..., tuple[VirtualEnv, Path]]
) -> None:
    # Establish that if we get a fully-qualified system path (on Windows
    # or otherwise) and the path exists, that we accept it.
    venv, _ = make_one(interpreter=r"c:\Python36\python.exe")

    which.return_value = venv.interpreter
    assert venv._resolved_interpreter == r"c:\Python36\python.exe"
    which.assert_called_once_with(r"c:\Python36\python.exe")


@pytest.mark.parametrize(
    ("input_", "expected"),
    [
        ("3.7", r"c:\python37-x64\python.exe"),
        ("python3.6", r"c:\python36-x64\python.exe"),
        ("2.7-32", r"c:\python27\python.exe"),
    ],
)
@mock.patch("nox.virtualenv._PLATFORM", new="win32")
@mock.patch.object(subprocess, "run")
@mock.patch.object(shutil, "which")
def test__resolved_interpreter_windows_pyexe(
    which: mock.Mock,
    run: mock.Mock,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
    input_: str,
    expected: str,
) -> None:
    # Establish that if we get a standard pythonX.Y path, we look it
    # up via the py launcher on Windows.
    venv, _ = make_one(interpreter=input_)

    if input_ == "3.7":
        input_ = "python3.7"

    # Trick the system into thinking that it cannot find python3.6
    # (it likely will on Unix). Also, when the system looks for the
    # py launcher, give it a dummy that returns our test value when
    # run.
    def special_run(cmd: str, *args: str, **kwargs: object) -> TextProcessResult:
        if cmd[0] == "py":
            return TextProcessResult(expected)
        return TextProcessResult("", 1)

    run.side_effect = special_run
    which.side_effect = lambda x: "py" if x == "py" else None

    # Okay now run the test.
    assert venv._resolved_interpreter == expected
    assert which.call_count == 2
    which.assert_has_calls([mock.call(input_), mock.call("py")])


@mock.patch("nox.virtualenv._PLATFORM", new="win32")
@mock.patch.object(subprocess, "run")
@mock.patch.object(shutil, "which")
def test__resolved_interpreter_windows_pyexe_fails(
    which: mock.Mock, run: mock.Mock, make_one: Callable[..., tuple[VirtualEnv, Path]]
) -> None:
    # Establish that if the py launcher fails, we give the right error.
    venv, _ = make_one(interpreter="python3.6")

    # Trick the nox.virtualenv into thinking that it cannot find python3.6
    # (it likely will on Unix). Also, when the nox.virtualenv looks for the
    # py launcher, give it a dummy that fails.
    def special_run(cmd: str, *args: str, **kwargs: object) -> TextProcessResult:  # noqa: ARG001
        return TextProcessResult("", 1)

    run.side_effect = special_run
    which.side_effect = lambda x: "py" if x == "py" else None

    # Okay now run the test.
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        print(venv._resolved_interpreter)

    which.assert_has_calls([mock.call("python3.6"), mock.call("py")])


@mock.patch("nox.virtualenv._PLATFORM", new="win32")
@mock.patch("nox.virtualenv.UV_VERSION", new=version.Version("0.3"))
def test__resolved_interpreter_windows_path_and_version(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
    patch_sysfind: Callable[..., None],
) -> None:
    # Establish that if we get a standard pythonX.Y path, we look it
    # up via the path on Windows.
    venv, _ = make_one(interpreter="3.7")

    # Trick the system into thinking that it cannot find
    # pythonX.Y up until the python-in-path check at the end.
    # Also, we don't give it a mock py launcher.
    # But we give it a mock python interpreter to find
    # in the system path.
    correct_path = r"c:\python37-x64\python.exe"
    patch_sysfind(
        only_find=("python", "python.exe"),
        sysfind_result=correct_path,
        sysexec_result="3.7.3\\n",
    )

    # Okay, now run the test.
    assert venv._resolved_interpreter == correct_path


@pytest.mark.parametrize("input_", ["2.7", "python3.7", "goofy"])
@pytest.mark.parametrize("sysfind_result", [r"c:\python37-x64\python.exe", None])
@pytest.mark.parametrize("sysexec_result", ["3.7.3\\n", RAISE_ERROR])
@mock.patch("nox.virtualenv._PLATFORM", new="win32")
@mock.patch("nox.virtualenv.UV_VERSION", new=version.Version("0.3"))
def test__resolved_interpreter_windows_path_and_version_fails(
    input_: str,
    sysfind_result: None | str,
    sysexec_result: str,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
    patch_sysfind: Callable[..., None],
) -> None:
    # Establish that if we get a standard pythonX.Y path, we look it
    # up via the path on Windows.
    venv, _ = make_one(interpreter=input_, download_python="never")

    # Trick the system into thinking that it cannot find
    # pythonX.Y up until the python-in-path check at the end.
    # Also, we don't give it a mock py launcher.
    # But we give it a mock python interpreter to find
    # in the system path.
    patch_sysfind(("python", "python.exe"), sysfind_result, sysexec_result)

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        print(venv._resolved_interpreter)


@mock.patch("nox.virtualenv._PLATFORM", new="win32")
@mock.patch.object(shutil, "which")
def test__resolved_interpreter_not_found(
    which: mock.Mock, make_one: Callable[..., tuple[VirtualEnv, Path]]
) -> None:
    # Establish that if an interpreter cannot be found at a standard
    # location on Windows, we raise a useful error.
    venv, _ = make_one(interpreter="python3.6", download_python="never")

    # We are on Windows, and nothing can be found.
    which.return_value = None

    # Run the test.
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        print(venv._resolved_interpreter)


@mock.patch("nox.virtualenv._PLATFORM", new="win32")
@mock.patch("nox.virtualenv.locate_via_py", new=lambda _: None)  # type: ignore[misc]  # noqa: PT008
def test__resolved_interpreter_nonstandard(
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    # Establish that we do not try to resolve non-standard locations
    # on Windows.
    venv, _ = make_one(interpreter="goofy")

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        print(venv._resolved_interpreter)


@mock.patch("nox.virtualenv._PLATFORM", new="linux")
@mock.patch.object(shutil, "which", return_value=True)
def test__resolved_interpreter_cache_result(
    which: mock.Mock, make_one: Callable[..., tuple[VirtualEnv, Path]]
) -> None:
    venv, _ = make_one(interpreter="3.6")

    assert venv._resolved is None
    assert venv._resolved_interpreter == "python3.6"
    which.assert_called_once_with("python3.6")
    # Check the cache and call again to make sure it is used.
    assert venv._resolved == "python3.6"
    assert venv._resolved_interpreter == "python3.6"
    assert which.call_count == 1


@mock.patch("nox.virtualenv._PLATFORM", new="linux")
@mock.patch.object(shutil, "which", return_value=None)
def test__resolved_interpreter_cache_failure(
    which: mock.Mock, make_one: Callable[..., tuple[VirtualEnv, Path]]
) -> None:
    venv, _ = make_one(interpreter="3.7-32")

    assert venv._resolved is None
    with pytest.raises(nox.virtualenv.InterpreterNotFound) as exc_info:
        print(venv._resolved_interpreter)
    caught = exc_info.value

    which.assert_called_once_with("3.7-32")
    # Check the cache and call again to make sure it is used.
    assert venv._resolved is caught
    with pytest.raises(nox.virtualenv.InterpreterNotFound):  # type: ignore[unreachable]
        print(venv._resolved_interpreter)
    assert which.call_count == 1


@pytest.mark.parametrize("venv_backend", ["uv", "venv", "virtualenv"])
@mock.patch("nox.virtualenv.pbs_install_python")
@mock.patch("nox.virtualenv.uv_install_python")
@mock.patch.object(shutil, "which", return_value="/usr/bin/python3.11")
def test_download_python_never_preexisting_interpreter(
    which: mock.Mock,
    uv_install_mock: mock.Mock,
    pbs_install_mock: mock.Mock,
    venv_backend: str,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one(
        interpreter="python3.11",
        venv_backend=venv_backend,
        download_python="never",
    )

    resolved_interpreter = venv._resolved_interpreter
    assert resolved_interpreter == "python3.11"
    which.assert_called_once_with("python3.11")

    # should never try to install
    uv_install_mock.assert_not_called()
    pbs_install_mock.assert_not_called()


@pytest.mark.parametrize("venv_backend", ["uv", "venv", "virtualenv"])
@mock.patch("nox.virtualenv.pbs_install_python")
@mock.patch("nox.virtualenv.uv_install_python")
@mock.patch.object(shutil, "which", return_value=None)
def test_download_python_never_missing_interpreter(
    which: mock.Mock,
    uv_install_mock: mock.Mock,
    pbs_install_mock: mock.Mock,
    venv_backend: str,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one(
        interpreter="python3.11",
        venv_backend=venv_backend,
        download_python="never",
    )
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        _ = venv._resolved_interpreter

    if IS_WINDOWS:
        which.assert_called_with("py")
    else:
        which.assert_called_with("python3.11")

    # should never try to install
    uv_install_mock.assert_not_called()
    pbs_install_mock.assert_not_called()


@pytest.mark.parametrize("venv_backend", ["uv", "venv", "virtualenv"])
@mock.patch("nox.virtualenv.pbs_install_python")
@mock.patch("nox.virtualenv.uv_install_python")
@mock.patch.object(shutil, "which", return_value="/usr/bin/python3.11")
def test_download_python_auto_preexisting_interpreter(
    which: mock.Mock,
    uv_install_mock: mock.Mock,
    pbs_install_mock: mock.Mock,
    venv_backend: str,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one(
        interpreter="python3.11",
        venv_backend=venv_backend,
        download_python="auto",
    )

    # no install needed
    uv_install_mock.assert_not_called()
    pbs_install_mock.assert_not_called()

    assert venv._resolved_interpreter == "python3.11"
    which.assert_called_with("python3.11")


@pytest.mark.parametrize("venv_backend", ["uv", "venv", "virtualenv"])
@mock.patch(
    "nox.virtualenv.pbs_install_python",
    return_value="/.local/share/nox/cpython@3.11.3/bin/python3.11",
)
@mock.patch(
    "nox.virtualenv.uv_install_python",
    return_value=True,
)
@mock.patch.object(shutil, "which", return_value=None)
def test_download_python_auto_missing_interpreter(
    which: mock.Mock,
    uv_install_mock: mock.Mock,
    pbs_install_mock: mock.Mock,
    venv_backend: str,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one(
        interpreter="python3.11",
        venv_backend=venv_backend,
        download_python="auto",
    )

    resolved_interpreter = venv._resolved_interpreter

    # make sure we tried to find an interpreter first
    which.assert_any_call("python3.11")

    # the resolved interpreter should be the one we install
    if venv_backend == "uv":
        uv_install_mock.assert_called_once_with("python3.11")
        pbs_install_mock.assert_not_called()
        assert resolved_interpreter == "python3.11"
    else:
        pbs_install_mock.assert_called_once_with("python3.11")
        uv_install_mock.assert_not_called()
        assert resolved_interpreter == "/.local/share/nox/cpython@3.11.3/bin/python3.11"


@pytest.mark.parametrize("venv_backend", ["uv", "venv", "virtualenv"])
@mock.patch(
    "nox.virtualenv.pbs_install_python",
    return_value="/.local/share/nox/cpython@3.11.3/bin/python3.11",
)
@mock.patch(
    "nox.virtualenv.uv_install_python",
    return_value=True,
)
@mock.patch.object(shutil, "which", return_value="/usr/bin/python3.11")
def test_download_python_always_preexisting_interpreter(
    which: mock.Mock,
    uv_install_mock: mock.Mock,
    pbs_install_mock: mock.Mock,
    venv_backend: str,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one(
        interpreter="python3.11",
        venv_backend=venv_backend,
        download_python="always",
    )

    resolved_interpreter = venv._resolved_interpreter

    # We should NOT try to find an existing interpreter
    which.assert_not_called()

    # the resolved interpreter should be the one we install
    if venv_backend == "uv":
        uv_install_mock.assert_called_once_with("python3.11")
        pbs_install_mock.assert_not_called()
        assert resolved_interpreter == "python3.11"
    else:
        pbs_install_mock.assert_called_once_with("python3.11")
        uv_install_mock.assert_not_called()
        assert resolved_interpreter == "/.local/share/nox/cpython@3.11.3/bin/python3.11"


@pytest.mark.parametrize("venv_backend", ["uv", "venv", "virtualenv"])
@pytest.mark.parametrize("download_python", ["always", "auto"])
@mock.patch("nox.virtualenv.pbs_install_python", return_value=None)
@mock.patch("nox.virtualenv.uv_install_python", return_value=False)
def test_download_python_failed_install(
    uv_install_mock: mock.Mock,
    pbs_install_mock: mock.Mock,
    download_python: str,
    venv_backend: str,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    venv, _ = make_one(
        interpreter="python3.11",
        venv_backend=venv_backend,
        download_python=download_python,
    )

    with mock.patch.object(shutil, "which", return_value=None) as _, pytest.raises(
        nox.virtualenv.InterpreterNotFound
    ):
        _ = venv._resolved_interpreter

    if venv_backend == "uv":
        uv_install_mock.assert_called_once_with("python3.11")
        pbs_install_mock.assert_not_called()
    else:
        pbs_install_mock.assert_called_once_with("python3.11")
        uv_install_mock.assert_not_called()


@pytest.mark.parametrize(
    ("implementation", "version", "dir_name", "expected"),
    [
        ("cpython", "3.11", "cpython@3.11.5", True),
        ("pypy", "3.8", "pypy@3.8.16", True),
        ("cpython", "3.12", "cpython@3.11.5", False),
        ("pypy", "3.11", "cpython@3.11.5", False),
    ],
)
def test_find_pbs_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    implementation: str,
    version: str,
    dir_name: str,
    expected: bool,
) -> None:
    """Test find_pbs_python deals with different python implementations/versions"""
    nox_pbs_pythons = tmp_path / "nox_pbs_pythons"
    monkeypatch.setattr("nox.virtualenv.NOX_PBS_PYTHONS", nox_pbs_pythons)

    python_dir = nox_pbs_pythons / dir_name
    if IS_WINDOWS:
        python_dir.mkdir(parents=True)
        python = python_dir / "python.exe"
    else:
        bin_dir = python_dir / "bin"
        bin_dir.mkdir(parents=True)
        python = bin_dir / "python"
    python.touch()

    result = nox.virtualenv._find_pbs_python(implementation, version)
    if expected:
        assert result == str(python)
    else:
        assert result is None


def test_find_pbs_python_missing_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nox_pbs_pythons = tmp_path / "nox_pbs_pythons"
    monkeypatch.setattr("nox.virtualenv.NOX_PBS_PYTHONS", nox_pbs_pythons)

    python_dir = nox_pbs_pythons / "cpython@3.11.5"
    if IS_WINDOWS:
        python_dir.mkdir(parents=True)
    else:
        bin_dir = python_dir / "bin"
        bin_dir.mkdir(parents=True)

    assert nox.virtualenv._find_pbs_python("cpython", "3.11") is None


@mock.patch("nox.virtualenv._find_pbs_python", return_value="/existing/python/path")
def test_pbs_install_python_already_installed(find_pbs_mock: mock.Mock) -> None:
    """Test pbs_install_python early return when it was already installed"""
    result = nox.virtualenv.pbs_install_python("python3.11")

    assert result == "/existing/python/path"
    find_pbs_mock.assert_called_once_with("cpython", "3.11")


@mock.patch("nox.virtualenv.pbs_installer")
def test_pbs_install_python_success(
    pbs_installer_mock: mock.Mock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nox_pbs_pythons = tmp_path / "nox_pbs_pythons"
    monkeypatch.setattr("nox.virtualenv.NOX_PBS_PYTHONS", nox_pbs_pythons)

    # fake the installation
    python_dir = nox_pbs_pythons / "cpython@3.11.5"
    if IS_WINDOWS:
        python_dir.mkdir(parents=True)
        python_exe = python_dir / "python.exe"
    else:
        bin_dir = python_dir / "bin"
        bin_dir.mkdir(parents=True)
        python_exe = bin_dir / "python"

    def mock_install(*args: Any, **kwargs: Any) -> None:
        python_exe.touch()

    pbs_installer_mock.install.side_effect = mock_install

    result = nox.virtualenv.pbs_install_python("python3.11")
    # return value is a path to the executable
    assert result == str(python_exe)


@pytest.mark.parametrize("download_python", ["always", "auto"])
@mock.patch("nox.virtualenv.HAS_UV", new=True)
@mock.patch("nox.virtualenv.UV_VERSION", new=version.Version("0.4.0"))
@mock.patch("nox.virtualenv.uv_install_python", return_value=True)
@mock.patch.object(shutil, "which", return_value=None)
def test_download_python_uv_unsupported_version(
    which: mock.Mock,
    uv_install_mock: mock.Mock,
    download_python: str,
    make_one: Callable[..., tuple[VirtualEnv, Path]],
) -> None:
    """Test we dont install for unsupported uv versions"""
    venv, _ = make_one(
        interpreter="python3.11",
        venv_backend="uv",
        download_python=download_python,
    )

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        _ = venv._resolved_interpreter

    uv_install_mock.assert_not_called()
    if download_python == "always":
        which.assert_not_called()
    else:  # auto
        which.assert_any_call("python3.11")
