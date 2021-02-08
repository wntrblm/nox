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

import os
import shutil
import sys
from unittest import mock

import nox.virtualenv
import py
import pytest

IS_WINDOWS = nox.virtualenv._SYSTEM == "Windows"
HAS_CONDA = shutil.which("conda") is not None
RAISE_ERROR = "RAISE_ERROR"


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
def make_mocked_interpreter_path():
    """Provides a factory to create a mocked ``path`` object pointing
    to a python interpreter.

    This mocked ``path`` provides
        - a ``__str__`` which is equal to the factory's ``path`` parameter
        - a ``sysexec`` method which returns the value of the
          factory's ``sysexec_result`` parameter.
          (the ``sysexec_result`` parameter can be a version string
          or ``RAISE_ERROR``).
    """

    def factory(path, sysexec_result):
        def mock_sysexec(*_):
            if sysexec_result == RAISE_ERROR:
                raise py.process.cmdexec.Error(1, 1, "", "", "")
            else:
                return sysexec_result

        attrs = {
            "sysexec.side_effect": mock_sysexec,
            "__str__": mock.Mock(return_value=path),
        }
        mock_python = mock.Mock()
        mock_python.configure_mock(**attrs)

        return mock_python

    return factory


@pytest.fixture
def patch_sysfind(make_mocked_interpreter_path):
    """Provides a function to patch ``sysfind`` with parameters for tests related
    to locating a Python interpreter in the system ``PATH``.
    """

    def patcher(sysfind, only_find, sysfind_result, sysexec_result):
        """Returns an extended ``sysfind`` patch object for tests related to locating a
        Python interpreter in the system ``PATH``.

        Args:
            sysfind: The original sysfind patch object
            only_find (Tuple[str]): The strings for which ``sysfind`` should be successful,
                e.g. ``("python", "python.exe")``
            sysfind_result (Optional[str]): The ``path`` string to create the returned
                mocked ``path`` object with which will represent the found Python interpreter,
                or ``None``.
                This parameter is passed on to ``make_mocked_interpreter_path``.
            sysexec_result (str): A string that should be returned when executing the
                mocked ``path`` object. Usually a Python version string.
                Use the global ``RAISE_ERROR`` to have ``sysexec`` fail.
                This parameter is passed on to ``make_mocked_interpreter_path``.
        """
        mock_python = make_mocked_interpreter_path(sysfind_result, sysexec_result)

        def mock_sysfind(arg):
            if sysfind_result is None:
                return None
            elif arg.lower() in only_find:
                return mock_python
            else:
                return None

        sysfind.side_effect = mock_sysfind

        return sysfind

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

    # Test running create on an existing environment with reuse_exising
    # enabled, it should not be deleted.
    dir_.ensure("test.txt")
    assert dir_.join("test.txt").check()
    venv.reuse_existing = True
    venv.create()
    assert dir_.join("test.txt").check()


@pytest.mark.skipif(IS_WINDOWS, reason="Not testing multiple interpreters on Windows.")
@pytest.mark.skipif(not HAS_CONDA, reason="Missing conda command.")
def test_condaenv_create_interpreter(make_conda):
    venv, dir_ = make_conda(interpreter="3.7")
    venv.create()
    assert dir_.join("bin", "python").check()
    assert dir_.join("bin", "python3.7").check()


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
def test_condaenv_bin_windows(make_conda):
    venv, dir_ = make_conda()
    assert [dir_.strpath, dir_.join("Scripts").strpath] == venv.bin_paths


def test_condaenv_(make_conda):
    venv, dir_ = make_conda()
    assert not venv.is_offline()


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


def test_create(make_one):
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

    # Test running create on an existing environment with reuse_exising
    # enabled, it should not be deleted.
    dir_.ensure("test.txt")
    assert dir_.join("test.txt").check()
    venv.reuse_existing = True
    venv.create()
    assert dir_.join("test.txt").check()


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
@mock.patch.object(py.path.local, "sysfind", return_value=True)
def test__resolved_interpreter_numerical_non_windows(
    sysfind, make_one, input_, expected
):
    venv, _ = make_one(interpreter=input_)

    assert venv._resolved_interpreter == expected
    sysfind.assert_called_once_with(expected)


@pytest.mark.parametrize("input_", ["2.", "2.7."])
@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(py.path.local, "sysfind", return_value=False)
def test__resolved_interpreter_invalid_numerical_id(sysfind, make_one, input_):
    venv, _ = make_one(interpreter=input_)

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter

    sysfind.assert_called_once_with(input_)


@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(py.path.local, "sysfind", return_value=False)
def test__resolved_interpreter_32_bit_non_windows(sysfind, make_one):
    venv, _ = make_one(interpreter="3.6-32")

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter
    sysfind.assert_called_once_with("3.6-32")


@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(py.path.local, "sysfind", return_value=True)
def test__resolved_interpreter_non_windows(sysfind, make_one):
    # Establish that the interpreter is simply passed through resolution
    # on non-Windows.
    venv, _ = make_one(interpreter="python3.6")

    assert venv._resolved_interpreter == "python3.6"
    sysfind.assert_called_once_with("python3.6")


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
@mock.patch.object(py.path.local, "sysfind")
def test__resolved_interpreter_windows_full_path(sysfind, make_one):
    # Establish that if we get a fully-qualified system path (on Windows
    # or otherwise) and the path exists, that we accept it.
    venv, _ = make_one(interpreter=r"c:\Python36\python.exe")

    sysfind.return_value = py.path.local(venv.interpreter)
    assert venv._resolved_interpreter == r"c:\Python36\python.exe"
    sysfind.assert_called_once_with(r"c:\Python36\python.exe")


@pytest.mark.parametrize(
    ["input_", "expected"],
    [
        ("3.7", r"c:\python37-x64\python.exe"),
        ("python3.6", r"c:\python36-x64\python.exe"),
        ("2.7-32", r"c:\python27\python.exe"),
    ],
)
@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
@mock.patch.object(py.path.local, "sysfind")
def test__resolved_interpreter_windows_pyexe(sysfind, make_one, input_, expected):
    # Establish that if we get a standard pythonX.Y path, we look it
    # up via the py launcher on Windows.
    venv, _ = make_one(interpreter=input_)

    # Trick the system into thinking that it cannot find python3.6
    # (it likely will on Unix). Also, when the system looks for the
    # py launcher, give it a dummy that returns our test value when
    # run.
    attrs = {"sysexec.return_value": expected}
    mock_py = mock.Mock()
    mock_py.configure_mock(**attrs)
    sysfind.side_effect = lambda arg: mock_py if arg == "py" else None

    # Okay now run the test.
    assert venv._resolved_interpreter == expected
    assert sysfind.call_count == 2
    if input_ == "3.7":
        sysfind.assert_has_calls([mock.call("python3.7"), mock.call("py")])
    else:
        sysfind.assert_has_calls([mock.call(input_), mock.call("py")])


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
@mock.patch.object(py.path.local, "sysfind")
def test__resolved_interpreter_windows_pyexe_fails(sysfind, make_one):
    # Establish that if the py launcher fails, we give the right error.
    venv, _ = make_one(interpreter="python3.6")

    # Trick the nox.virtualenv._SYSTEM into thinking that it cannot find python3.6
    # (it likely will on Unix). Also, when the nox.virtualenv._SYSTEM looks for the
    # py launcher, give it a dummy that fails.
    attrs = {"sysexec.side_effect": py.process.cmdexec.Error(1, 1, "", "", "")}
    mock_py = mock.Mock()
    mock_py.configure_mock(**attrs)
    sysfind.side_effect = lambda arg: mock_py if arg == "py" else None

    # Okay now run the test.
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter

    sysfind.assert_any_call("python3.6")
    sysfind.assert_any_call("py")


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
@mock.patch.object(py.path.local, "sysfind")
def test__resolved_interpreter_windows_path_and_version(
    sysfind, make_one, patch_sysfind
):
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
        sysfind,
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
@mock.patch.object(py.path.local, "sysfind")
def test__resolved_interpreter_windows_path_and_version_fails(
    sysfind, input_, sysfind_result, sysexec_result, make_one, patch_sysfind
):
    # Establish that if we get a standard pythonX.Y path, we look it
    # up via the path on Windows.
    venv, _ = make_one(interpreter=input_)

    # Trick the system into thinking that it cannot find
    # pythonX.Y up until the python-in-path check at the end.
    # Also, we don't give it a mock py launcher.
    # But we give it a mock python interpreter to find
    # in the system path.
    patch_sysfind(sysfind, ("python", "python.exe"), sysfind_result, sysexec_result)

    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
@mock.patch.object(py._path.local.LocalPath, "check")
@mock.patch.object(py.path.local, "sysfind")
def test__resolved_interpreter_not_found(sysfind, check, make_one):
    # Establish that if an interpreter cannot be found at a standard
    # location on Windows, we raise a useful error.
    venv, _ = make_one(interpreter="python3.6")

    # We are on Windows, and nothing can be found.
    sysfind.return_value = None
    check.return_value = False

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
@mock.patch.object(py.path.local, "sysfind", return_value=True)
def test__resolved_interpreter_cache_result(sysfind, make_one):
    venv, _ = make_one(interpreter="3.6")

    assert venv._resolved is None
    assert venv._resolved_interpreter == "python3.6"
    sysfind.assert_called_once_with("python3.6")
    # Check the cache and call again to make sure it is used.
    assert venv._resolved == "python3.6"
    assert venv._resolved_interpreter == "python3.6"
    assert sysfind.call_count == 1


@mock.patch("nox.virtualenv._SYSTEM", new="Linux")
@mock.patch.object(py.path.local, "sysfind", return_value=None)
def test__resolved_interpreter_cache_failure(sysfind, make_one):
    venv, _ = make_one(interpreter="3.7-32")

    assert venv._resolved is None
    with pytest.raises(nox.virtualenv.InterpreterNotFound) as exc_info:
        venv._resolved_interpreter
    caught = exc_info.value

    sysfind.assert_called_once_with("3.7-32")
    # Check the cache and call again to make sure it is used.
    assert venv._resolved is caught
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter
    assert sysfind.call_count == 1
