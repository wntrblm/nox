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

import imp
import os
import sys
from unittest import mock

import py
import pytest

import nox.command
import nox.virtualenv


IS_WINDOWS = nox.virtualenv._SYSTEM == "Windows"


@pytest.fixture
def make_one(tmpdir):
    def factory(*args, **kwargs):
        location = tmpdir.join("venv")
        venv = nox.virtualenv.VirtualEnv(location.strpath, *args, **kwargs)
        return (venv, location)

    return factory


def test_process_env_constructor():
    penv = nox.virtualenv.ProcessEnv()
    assert not penv.bin

    penv = nox.virtualenv.ProcessEnv(env={"SIGIL": "123"})
    assert penv.env["SIGIL"] == "123"


def test_constructor_defaults(make_one):
    venv, _ = make_one()
    assert venv.location
    assert venv.interpreter is None
    assert venv.reuse_existing is False


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
    assert venv.bin in venv.env["PATH"]
    assert venv.bin not in os.environ["PATH"]


def test_blacklisted_env(monkeypatch, make_one):
    monkeypatch.setenv("__PYVENV_LAUNCHER__", "meep")
    venv, _ = make_one()
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


def test_bin(make_one):
    venv, dir_ = make_one()

    if IS_WINDOWS:
        assert dir_.join("Scripts").strpath == venv.bin
    else:
        assert dir_.join("bin").strpath == venv.bin


@mock.patch("nox.virtualenv._SYSTEM", new="Windows")
def test_bin_windows(make_one):
    venv, dir_ = make_one()
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


@pytest.mark.skipif(IS_WINDOWS, reason="Not testing multiple interpreters on Windows.")
def test_create_interpreter(make_one):
    venv, dir_ = make_one(interpreter="python3")
    venv.create()
    assert dir_.join("bin", "python").check()
    assert dir_.join("bin", "python3").check()


@mock.patch(
    "sys._MEIPASS",
    new=r"c:\\Windows\TEMP\_MEIxxx" if IS_WINDOWS else "/tmp/_MEIxxx",
    create=True,
)
@mock.patch.object(nox.command, "run")
@mock.patch.object(py.path.local, "sysfind", side_effect=[False, False, True])
@mock.patch("nox.virtualenv._FROZEN", new=True)
def test_create_frozen(sysfind, run, make_one):
    # Establish that the cmdline passed to nox.command.run, when nox is frozen
    # is correctly built
    venv, dir_ = make_one(interpreter=None)
    venv.create()
    virtualenv_mod_path = os.path.join(sys._MEIPASS, "site-packages", "virtualenv.py")
    run.assert_called_once_with(
        ["python2.7", virtualenv_mod_path, dir_.strpath], log=False, silent=True
    )


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
    sysfind.side_effect = lambda arg: mock_py if arg == "py" else False

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
    sysfind.side_effect = lambda arg: mock_py if arg == "py" else False

    # Okay now run the test.
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter

    sysfind.assert_any_call("python3.6")
    sysfind.assert_any_call("py")


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


def test__runtime_interpreter(make_one):
    # Establish that the _runtime_interpreter method, when nox is not frozen
    # is set to the current sys.executable
    venv, _ = make_one(interpreter=None)
    assert venv._runtime_interpreter == sys.executable


@mock.patch("nox.virtualenv._FROZEN", new=True)
def test__runtime_interpreter_frozen(make_one):
    # Establish that the _runtime_interpreter method, when nox is frozen
    # is set to the current sys.executable(because it was found)
    venv, _ = make_one(interpreter=None)
    executable = os.path.basename(sys.executable)
    if IS_WINDOWS:
        executable += ".exe"
    assert venv._runtime_interpreter == executable


@mock.patch.object(py.path.local, "sysfind", side_effect=[False, True])
@mock.patch("nox.virtualenv._FROZEN", new=True)
def test__runtime_interpreter_frozen_python3(sysfind, make_one):
    # Establish that the _runtime_interpreter method, when nox is frozen
    # is set to python3 because it couldn't find python3.<minor>
    venv, _ = make_one(interpreter=None)
    assert venv._runtime_interpreter == "python3"
    assert sysfind.call_count == 2


@mock.patch.object(py.path.local, "sysfind", return_value=False)
@mock.patch("nox.virtualenv._FROZEN", new=True)
def test__runtime_interpreter_frozen_not_found(sysfind, make_one):
    # Establish that if no python binary is found, when nox is frozen,
    # nox will raise InterpreterNotFound
    venv, _ = make_one(interpreter=None)
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter
    # The call cound will be 5 because we'll search for:
    # python<major>.<minor>
    # python<major>
    # python2.7
    # python2
    # python
    #
    # <major> and <minor>, when nox is frozen, are relative to the Python
    # <major> and <minor> at the time nox was compiled
    assert sysfind.call_count == 5


@mock.patch.object(py.path.local, "sysfind", return_value=False)
@mock.patch("nox.virtualenv._FROZEN", new=True)
def test__runtime_interpreter_frozen_not_found_cached(sysfind, make_one):
    # Establish that if no python binary is found, when nox is frozen,
    # that the _runtime_interpreter propery is cached
    venv, _ = make_one(interpreter=None)
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter
    assert sysfind.call_count == 5

    # _resolved should now be cached to an exception
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter

    # The count hasn't changed
    assert sysfind.call_count == 5


@mock.patch("nox.command.run", new=mock.MagicMock(return_value="Python 2.6.6"))
@mock.patch.object(
    py.path.local, "sysfind", side_effect=[False, False, False, True, True]
)
@mock.patch("nox.virtualenv._FROZEN", new=True)
def test__runtime_interpreter_frozen_reject_python26(sysfind, make_one):
    # Establish that if a python 2.6 binary is found, when nox is frozen,
    # nox will raise InterpreterNotFound because pip/virtualenv won't even
    # play nice with pytohn 2.6
    venv, _ = make_one(interpreter=None)
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter
    # The call cound will be 5 because we'll search for:
    # python<major>.<minor>
    # python<major>
    # python2.7
    # python2
    # python
    #
    # <major> and <minor>, when nox is frozen, are relative to the Python
    # <major> and <minor> at the time nox was compiled
    assert sysfind.call_count == 5


@mock.patch("nox.command.run", new=mock.MagicMock(return_value="Python 2.a.6"))
@mock.patch.object(
    py.path.local, "sysfind", side_effect=[False, False, False, True, True]
)
@mock.patch("nox.virtualenv._FROZEN", new=True)
def test__runtime_interpreter_frozen_fails_to_parse_version(sysfind, make_one):
    # Establish that if no python binary is found, when nox is frozen,
    # nox will raise InterpreterNotFound because it couldn't properly parse
    # the python version
    venv, _ = make_one(interpreter=None)
    with pytest.raises(nox.virtualenv.InterpreterNotFound):
        venv._resolved_interpreter
    assert sysfind.call_count == 5


@mock.patch("nox.command.run", new=mock.MagicMock(return_value="Python 2.7.15"))
@mock.patch.object(
    py.path.local, "sysfind", side_effect=[False, False, False, False, True]
)
@mock.patch("nox.virtualenv._FROZEN", new=True)
def test__runtime_interpreter_frozen_accept_python27(sysfind, make_one):
    # Establish that nox is happy with a python binary, when nox is frozen,
    # that reports as being 2.7
    venv, _ = make_one(interpreter=None)
    assert venv._resolved_interpreter == "python"
    # The call cound will be 5 because we'll search for:
    # python<major>.<minor>
    # python<major>
    # python2.7
    # python2
    # python
    #
    # <major> and <minor>, when nox is frozen, are relative to the Python
    # <major> and <minor> at the time nox was compiled
    assert sysfind.call_count == 5


@mock.patch("nox.command.run", new=mock.MagicMock(return_value="Python 2.7.15"))
@mock.patch.object(
    py.path.local, "sysfind", side_effect=[False, False, False, False, True]
)
@mock.patch("nox.virtualenv._FROZEN", new=True)
def test__runtime_interpreter_frozen_accept_python27_cached(sysfind, make_one):
    # Establish that the _runtime_interpreter property is cached
    venv, _ = make_one(interpreter=None)
    assert venv._resolved_interpreter == "python"
    assert sysfind.call_count == 5
    # The propery should be cached now
    assert venv._resolved_interpreter == "python"
    # Call count should be the same
    assert sysfind.call_count == 5


def test__frozen_attribute_missing():
    # Establish that _FROZEN is set to False when nox is not frozen
    assert nox.virtualenv._FROZEN is False


@mock.patch.object(sys, "frozen", new=True, create=True)
def test__frozen_attribute_present():
    # Establish that _FROZEN is set to True when nox is not frozen
    # Since _FROZEN is set at the module level, we need to reload nox.virtualenv
    # because the module is already imported
    imp.reload(nox.virtualenv)
    assert nox.virtualenv._FROZEN is True
