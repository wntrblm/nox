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

import os
import re
import shutil
import subprocess
import sys
from textwrap import dedent
from typing import NamedTuple
from unittest import mock

import pytest
import virtualenv
from packaging import version

import nox.virtualenv

IS_WINDOWS = nox.virtualenv._SYSTEM == "Windows"
HAS_CONDA = shutil.which("conda") is not None
RAISE_ERROR = "RAISE_ERROR"
VIRTUALENV_VERSION = virtualenv.__version__


class TextProcessResult(NamedTuple):
    stdout: str
    returncode: int = 0


@pytest.fixture
def make_one(tmpdir):
    def factory(*args, **kwargs):
        location = tmpdir.join("venv")
        venv = nox.virtualenv.VirtualEnv(location.strpath, *args, **kwargs)
        return (venv, location)

    return factory


@pytest.fixture
def make_conda(tmpdir):
    def factory(*args, **kwargs):
        location = tmpdir.join("condaenv")
        venv = nox.virtualenv.CondaEnv(location.strpath, *args, **kwargs)
        return (venv, location)

    return factory


@pytest.fixture
def patch_sysfind(monkeypatch):
    """Provides a function to patch ``sysfind`` with parameters for tests related
    to locating a Python interpreter in the system ``PATH``.
    """

    def patcher(only_find, sysfind_result, sysexec_result):
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

        def special_which(name, path=None):
            if sysfind_result is None:
                return None
            if name.lower() in only_find:
                return sysfind_result or name
            return None

        monkeypatch.setattr(shutil, "which", special_which)

        def special_run(cmd, *args, **kwargs):
            return TextProcessResult(sysexec_result)

        monkeypatch.setattr(subprocess, "run", special_run)

    return patcher


def test_process_env_constructor():
    penv = nox.virtualenv.ProcessEnv()
    assert not penv.bin_paths
    with pytest.raises(
        ValueError, match=r"^The environment does not have a bin directory\.$"
    ):
        penv.bin

    penv = nox.virtualenv.ProcessEnv(env={"SIGIL": "123"})
    assert penv.env["SIGIL"] == "123"

    penv = nox.virtualenv.ProcessEnv(bin_paths=["/bin"])
    assert penv.bin == "/bin"


def test_process_env_create():
    penv = nox.virtualenv.ProcessEnv()
    with pytest.raises(NotImplementedError):
        penv.create()


def test_condaenv_constructor_defaults(make_conda):
    venv, _ = make_conda()
    assert venv.location
    assert venv.interpreter is None
    assert venv.reuse_existing is False


def test_condaenv_constructor_explicit(make_conda):
    venv, _ = make_conda(interpreter="3.5", reuse_existing=True)
    assert venv.location
    assert venv.interpreter == "3.5"
    assert venv.reuse_existing is True


@pytest.mark.skipif(not HAS_CONDA, reason="Missing conda command.")
def test_condaenv_create(make_conda):
    venv, dir_ = make_conda()
    venv.create()

    if IS_WINDOWS:
        assert dir_.join("python.exe").check()
        assert dir_.join("Scripts", "pip.exe").check()
        assert dir_.join("Library").check()
    else:
        assert dir_.join("bin", "python").check()
        assert dir_.join("bin", "pip").check()
        assert dir_.join("lib").check()

    # Test running create on an existing environment. It should be deleted.
    dir_.ensure("test.txt")
    venv.create()
    assert not dir_.join("test.txt").check()

    # Test running create on an existing environment with reuse_existing
    # enabled, it should not be deleted.
    dir_.ensure("test.txt")
    assert dir_.join("test.txt").check()
    venv.reuse_existing = True
    venv.create()
    assert dir_.join("test.txt").check()
    assert venv._reused


@pytest.mark.skipif(not HAS_CONDA, reason="Missing conda command.")
def test_condaenv_create_with_params(make_conda):
    venv, dir_ = make_conda(venv_params=["--verbose"])
    venv.create()
    if IS_WINDOWS:
        assert dir_.join("python.exe").check()
        assert dir_.join("Scripts", "pip.exe").check()
    else:
        assert dir_.join("bin", "python").check()
        assert dir_.join("bin", "pip").check()


@pytest.mark.skipif(not HAS_CONDA, reason="Missing conda command.")
def test_condaenv_create_interpreter(make_conda):
    venv, dir_ = make_conda(interpreter="3.7")
    venv.create()
    if IS_WINDOWS:
        assert dir_.join("python.exe").check()
        assert dir_.join("python37.dll").check()
        assert dir_.join("python37.pdb").check()
        assert not dir_.join("python37.exe").check()
    else:
        assert dir_.join("bin", "python").check()
        assert dir_.join("bin", "python3.7").check()


@pytest.mark.skipif(not HAS_CONDA, reason="Missing conda command.")
def test_conda_env_create_verbose(make_conda):
    venv, dir_ = make_conda()
    with mock.patch("nox.virtualenv.nox.command.run") as mock_run:
        venv.create()

    args, kwargs = mock_run.call_args
    assert kwargs["log"] is False

    nox.options.verbose = True
    with mock.patch("nox.virtualenv.nox.command.run") as mock_run:
        venv.create()

    args, kwargs = mock_run.call_args
    assert kwargs["log"]


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
def test_condaenv_bin_windows(make_conda):
    venv, dir_ = make_conda()
    assert [
        dir_.strpath,
        dir_.join("Library", "mingw-w64", "bin").strpath,
        dir_.join("Library", "usr", "bin").strpath,
        dir_.join("Library", "bin").strpath,
        dir_.join("Scripts").strpath,
        dir_.join("bin").strpath,
    ] == venv.bin_paths


@pytest.mark.skipif(not HAS_CONDA, reason="Missing conda command.")
def test_condaenv_(make_conda):
    venv, dir_ = make_conda()
    assert not venv.is_offline()


@pytest.mark.skipif(not HAS_CONDA, reason="Missing conda command.")
def test_condaenv_detection(make_conda):
    venv, dir_ = make_conda()
    venv.create()

    proc_result = subprocess.run(
        [shutil.which("conda"), "list"],
        env=venv.env,
        check=True,
        capture_output=True,
    )
    output = proc_result.stdout.decode()
    path_regex = re.compile(r"packages in environment at (?P<env_dir>.+):")

    assert path_regex.search(output).group("env_dir") == dir_.strpath


def test_constructor_defaults(make_one):
    venv, _ = make_one()
    assert venv.location
    assert venv.interpreter is None
    assert venv.reuse_existing is False
    assert venv.venv_or_virtualenv == "virtualenv"


@pytest.mark.skipif(IS_WINDOWS, reason="Not testing multiple interpreters on Windows.")
def test_constructor_explicit(make_one):
    venv, _ = make_one(interpreter="python3.5", reuse_existing=True)
    assert venv.location
    assert venv.interpreter == "python3.5"
    assert venv.reuse_existing is True


def test_env(monkeypatch, make_one):
    monkeypatch.setenv("SIGIL", "123")
    venv, _ = make_one()
    assert venv.env["SIGIL"] == "123"
    assert len(venv.bin_paths) == 1
    assert venv.bin_paths[0] in venv.env["PATH"]
    assert venv.bin_paths[0] not in os.environ["PATH"]


def test_blacklisted_env(monkeypatch, make_one):
    monkeypatch.setenv("__PYVENV_LAUNCHER__", "meep")
    venv, _ = make_one()
    assert len(venv.bin_paths) == 1
    assert venv.bin_paths[0] == venv.bin
    assert "__PYVENV_LAUNCHER__" not in venv.bin


def test__clean_location(monkeypatch, make_one):
    venv, dir_ = make_one()

    # Don't re-use existing, but doesn't currently exist.
    # Should return True indicating that the venv needs to be created.
    monkeypatch.setattr(
        nox.virtualenv.VirtualEnv, "_check_reused_environment_type", mock.MagicMock()
    )
    monkeypatch.setattr(
        nox.virtualenv.VirtualEnv,
        "_check_reused_environment_interpreter",
        mock.MagicMock(),
    )
    monkeypatch.delattr(nox.virtualenv.shutil, "rmtree")
    assert not dir_.check()
    assert venv._clean_location()

    # Re-use existing, and currently exists.
    # Should return False indicating that the venv doesn't need to be created.
    dir_.mkdir()
    assert dir_.check()
    venv.reuse_existing = True
    assert not venv._clean_location()

    # Don't re-use existing, and currently exists.
    # Should return True indicating the venv needs to be created.
    monkeypatch.undo()
    assert dir_.check()
    venv.reuse_existing = False
    assert venv._clean_location()
    assert not dir_.check()

    # Re-use existing, but doesn't exist.
    # Should return True indicating the venv needs to be created.
    venv.reuse_existing = True
    assert venv._clean_location()


def test_bin_paths(make_one):
    venv, dir_ = make_one()

    assert len(venv.bin_paths) == 1
    assert venv.bin_paths[0] == venv.bin

    if IS_WINDOWS:
        assert dir_.join("Scripts").strpath == venv.bin
    else:
        assert dir_.join("bin").strpath == venv.bin


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
def test_bin_windows(make_one):
    venv, dir_ = make_one()
    assert len(venv.bin_paths) == 1
    assert venv.bin_paths[0] == venv.bin
    assert dir_.join("Scripts").strpath == venv.bin


def test_create(monkeypatch, make_one):
    venv, dir_ = make_one()
    venv.create()

    if IS_WINDOWS:
        assert dir_.join("Scripts", "python.exe").check()
        assert dir_.join("Scripts", "pip.exe").check()
        assert dir_.join("Lib").check()
    else:
        assert dir_.join("bin", "python").check()
        assert dir_.join("bin", "pip").check()
        assert dir_.join("lib").check()

    # Test running create on an existing environment. It should be deleted.
    dir_.ensure("test.txt")
    venv.create()
    assert not dir_.join("test.txt").check()

    # Test running create on an existing environment with reuse_existing
    # enabled, it should not be deleted.
    dir_.ensure("test.txt")
    assert dir_.join("test.txt").check()
    venv.reuse_existing = True

    venv.create()

    assert venv._reused
    assert dir_.join("test.txt").check()


def test_create_reuse_environment(make_one):
    venv, location = make_one(reuse_existing=True)
    venv.create()

    reused = not venv.create()

    assert reused


@pytest.fixture
def _enable_staleness_check(monkeypatch):
    monkeypatch.setattr("nox.virtualenv._ENABLE_STALENESS_CHECK", True)


enable_staleness_check = pytest.mark.usefixtures("_enable_staleness_check")


@enable_staleness_check
def test_create_reuse_environment_with_different_interpreter(make_one, monkeypatch):
    venv, location = make_one(reuse_existing=True)
    venv.create()

    # Pretend that the environment was created with a different interpreter.
    monkeypatch.setattr(venv, "_check_reused_environment_interpreter", lambda: False)

    # Create a marker file. It should be gone after the environment is re-created.
    location.join("marker").ensure()

    reused = not venv.create()

    assert not reused
    assert not location.join("marker").check()


@enable_staleness_check
def test_create_reuse_stale_venv_environment(make_one):
    venv, location = make_one(reuse_existing=True)
    venv.create()

    # Drop a venv-style pyvenv.cfg into the environment.
    pyvenv_cfg = """\
    home = /usr/bin
    include-system-site-packages = false
    version = 3.9.6
    """
    location.join("pyvenv.cfg").write(dedent(pyvenv_cfg))

    reused = not venv.create()

    # The environment is not reused because it does not look like a
    # virtualenv-style environment.
    assert not reused


@enable_staleness_check
def test_create_reuse_stale_virtualenv_environment(make_one):
    venv, location = make_one(reuse_existing=True, venv=True)
    venv.create()

    # Drop a virtualenv-style pyvenv.cfg into the environment.
    pyvenv_cfg = """\
    home = /usr
    implementation = CPython
    version_info = 3.9.6.final.0
    virtualenv = 20.4.6
    include-system-site-packages = false
    base-prefix = /usr
    base-exec-prefix = /usr
    base-executable = /usr/bin/python3.9
    """
    location.join("pyvenv.cfg").write(dedent(pyvenv_cfg))

    reused = not venv.create()

    # The environment is not reused because it does not look like a
    # venv-style environment.
    assert not reused


@enable_staleness_check
def test_create_reuse_venv_environment(make_one):
    venv, location = make_one(reuse_existing=True, venv=True)
    venv.create()

    # Place a spurious occurrence of "virtualenv" in the pyvenv.cfg.
    pyvenv_cfg = location.join("pyvenv.cfg")
    pyvenv_cfg.write(pyvenv_cfg.read() + "bogus = virtualenv\n")

    reused = not venv.create()

    # The environment should be detected as venv-style and reused.
    assert reused


@enable_staleness_check
@pytest.mark.skipif(IS_WINDOWS, reason="Avoid 'No pyvenv.cfg file' error on Windows.")
def test_create_reuse_oldstyle_virtualenv_environment(make_one):
    venv, location = make_one(reuse_existing=True)
    venv.create()

    pyvenv_cfg = location.join("pyvenv.cfg")
    if not pyvenv_cfg.check():
        pytest.skip("Requires virtualenv >= 20.0.0.")

    # virtualenv < 20.0.0 does not create a pyvenv.cfg file.
    pyvenv_cfg.remove()

    reused = not venv.create()

    # The environment is detected as virtualenv-style and reused.
    assert reused


@enable_staleness_check
@pytest.mark.skipif(IS_WINDOWS, reason="Avoid 'No pyvenv.cfg file' error on Windows.")
def test_inner_functions_reusing_venv(make_one):
    venv, location = make_one(reuse_existing=True)
    venv.create()

    # Drop a venv-style pyvenv.cfg into the environment.
    pyvenv_cfg = """\
    home = /usr/bin
    include-system-site-packages = false
    version = 3.10
    base-prefix = foo
    """
    location.join("pyvenv.cfg").write(dedent(pyvenv_cfg))

    base_prefix = venv._read_base_prefix_from_pyvenv_cfg()
    assert base_prefix == "foo"

    reused_interpreter = venv._check_reused_environment_interpreter()
    # The created won't match 'foo'
    assert not reused_interpreter


@enable_staleness_check
@pytest.mark.skipif(
    version.parse(VIRTUALENV_VERSION) >= version.parse("20.22.0"),
    reason="Python 2.7 unsupported for virtualenv>=20.22.0",
)
def test_create_reuse_python2_environment(make_one):
    venv, location = make_one(reuse_existing=True, interpreter="2.7")

    try:
        venv.create()
    except nox.virtualenv.InterpreterNotFound:
        pytest.skip("Requires Python 2.7 installation.")

    reused = not venv.create()

    assert reused


def test_create_venv_backend(make_one):
    venv, dir_ = make_one(venv=True)
    venv.create()


@pytest.mark.skipif(IS_WINDOWS, reason="Not testing multiple interpreters on Windows.")
def test_create_interpreter(make_one):
    venv, dir_ = make_one(interpreter="python3")
    venv.create()
    assert dir_.join("bin", "python").check()
    assert dir_.join("bin", "python3").check()


def test__resolved_interpreter_none(make_one):
    # Establish that the _resolved_interpreter method is a no-op if the
    # interpreter is not set.
    venv, _ = make_one(interpreter=None)
    assert venv._resolved_interpreter == sys.executable


@pytest.mark.parametrize(
    ["input_", "expected"],
    [
        ("3", "python3"),
        ("3.6", "python3.6"),
        ("3.6.2", "python3.6"),
        ("3.10", "python3.10"),
        ("2.7.15", "python2.7"),
    ],
)
@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(shutil, "which", return_value=True)
def test__resolved_interpreter_numerical_non_windows(which, make_one, input_, expected):
    venv, _ = make_one(interpreter=input_)

    assert venv._resolved_interpreter == expected
    which.assert_called_once_with(expected)


@pytest.mark.parametrize("input_", ["2.", "2.7."])
@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(shutil, "which", return_value=False)
def test__resolved_interpreter_invalid_numerical_id(which, make_one, input_):
    venv, _ = make_one(interpreter=input_)

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter

    which.assert_called_once_with(input_)


@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(shutil, "which", return_value=False)
def test__resolved_interpreter_32_bit_non_windows(which, make_one):
    venv, _ = make_one(interpreter="3.6-32")

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter
    which.assert_called_once_with("3.6-32")


@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(shutil, "which", return_value=True)
def test__resolved_interpreter_non_windows(which, make_one):
    # Establish that the interpreter is simply passed through resolution
    # on non-Windows.
    venv, _ = make_one(interpreter="python3.6")

    assert venv._resolved_interpreter == "python3.6"
    which.assert_called_once_with("python3.6")


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
@mock.patch.object(shutil, "which")
def test__resolved_interpreter_windows_full_path(which, make_one):
    # Establish that if we get a fully-qualified system path (on Windows
    # or otherwise) and the path exists, that we accept it.
    venv, _ = make_one(interpreter=r"c:\Python36\python.exe")

    which.return_value = venv.interpreter
    assert venv._resolved_interpreter == r"c:\Python36\python.exe"
    which.assert_called_once_with(r"c:\Python36\python.exe")


@pytest.mark.parametrize(
    ["input_", "expected"],
    [
        ("3.7", r"c:\python37-x64\python.exe"),
        ("python3.6", r"c:\python36-x64\python.exe"),
        ("2.7-32", r"c:\python27\python.exe"),
    ],
)
@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
@mock.patch.object(subprocess, "run")
@mock.patch.object(shutil, "which")
def test__resolved_interpreter_windows_pyexe(which, run, make_one, input_, expected):
    # Establish that if we get a standard pythonX.Y path, we look it
    # up via the py launcher on Windows.
    venv, _ = make_one(interpreter=input_)

    if input_ == "3.7":
        input_ = "python3.7"

    # Trick the system into thinking that it cannot find python3.6
    # (it likely will on Unix). Also, when the system looks for the
    # py launcher, give it a dummy that returns our test value when
    # run.
    def special_run(cmd, *args, **kwargs):
        if cmd[0] == "py":
            return TextProcessResult(expected)
        return TextProcessResult("", 1)

    run.side_effect = special_run
    which.side_effect = lambda x: "py" if x == "py" else None

    # Okay now run the test.
    assert venv._resolved_interpreter == expected
    assert which.call_count == 2
    which.assert_has_calls([mock.call(input_), mock.call("py")])


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
@mock.patch.object(subprocess, "run")
@mock.patch.object(shutil, "which")
def test__resolved_interpreter_windows_pyexe_fails(which, run, make_one):
    # Establish that if the py launcher fails, we give the right error.
    venv, _ = make_one(interpreter="python3.6")

    # Trick the nox.virtualenv._SYSTEM into thinking that it cannot find python3.6
    # (it likely will on Unix). Also, when the nox.virtualenv._SYSTEM looks for the
    # py launcher, give it a dummy that fails.
    def special_run(cmd, *args, **kwargs):
        return TextProcessResult("", 1)

    run.side_effect = special_run
    which.side_effect = lambda x: "py" if x == "py" else None

    # Okay now run the test.
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter

    which.assert_has_calls([mock.call("python3.6"), mock.call("py")])


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
def test__resolved_interpreter_windows_path_and_version(make_one, patch_sysfind):
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
@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
def test__resolved_interpreter_windows_path_and_version_fails(
    input_, sysfind_result, sysexec_result, make_one, patch_sysfind
):
    # Establish that if we get a standard pythonX.Y path, we look it
    # up via the path on Windows.
    venv, _ = make_one(interpreter=input_)

    # Trick the system into thinking that it cannot find
    # pythonX.Y up until the python-in-path check at the end.
    # Also, we don't give it a mock py launcher.
    # But we give it a mock python interpreter to find
    # in the system path.
    patch_sysfind(("python", "python.exe"), sysfind_result, sysexec_result)

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
@mock.patch.object(shutil, "which")
def test__resolved_interpreter_not_found(which, make_one):
    # Establish that if an interpreter cannot be found at a standard
    # location on Windows, we raise a useful error.
    venv, _ = make_one(interpreter="python3.6")

    # We are on Windows, and nothing can be found.
    which.return_value = None

    # Run the test.
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
def test__resolved_interpreter_nonstandard(make_one):
    # Establish that we do not try to resolve non-standard locations
    # on Windows.
    venv, _ = make_one(interpreter="goofy")

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter


@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(shutil, "which", return_value=True)
def test__resolved_interpreter_cache_result(which, make_one):
    venv, _ = make_one(interpreter="3.6")

    assert venv._resolved is None
    assert venv._resolved_interpreter == "python3.6"
    which.assert_called_once_with("python3.6")
    # Check the cache and call again to make sure it is used.
    assert venv._resolved == "python3.6"
    assert venv._resolved_interpreter == "python3.6"
    assert which.call_count == 1


@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(shutil, "which", return_value=None)
def test__resolved_interpreter_cache_failure(which, make_one):
    venv, _ = make_one(interpreter="3.7-32")

    assert venv._resolved is None
    with pytest.raises(nox.virtualenv.InterpreterNotFound) as exc_info:
        venv._resolved_interpreter
    caught = exc_info.value

    which.assert_called_once_with("3.7-32")
    # Check the cache and call again to make sure it is used.
    assert venv._resolved is caught
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter
    assert which.call_count == 1
