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

import logging
import os
import sys
from unittest import mock

import pytest

import nox.command

PYTHON = sys.executable


def test_run_defaults(capsys):
    result = nox.command.run([PYTHON, "-c", "print(123)"])

    assert result is True


def test_run_silent(capsys):
    result = nox.command.run([PYTHON, "-c", "print(123)"], silent=True)

    out, _ = capsys.readouterr()

    assert "123" in result
    assert out == ""


def test_run_env_unicode():
    result = nox.command.run(
        [PYTHON, "-c", 'import os; print(os.environ["SIGIL"])'],
        silent=True,
        env={u"SIGIL": u"123"},
    )

    assert "123" in result


def test_run_env_systemroot():
    systemroot = os.environ.setdefault("SYSTEMROOT", str("sigil"))

    result = nox.command.run(
        [PYTHON, "-c", 'import os; print(os.environ["SYSTEMROOT"])'], silent=True
    )

    assert systemroot in result


def test_run_not_found():
    with pytest.raises(nox.command.CommandFailed):
        nox.command.run(["nonexistentcmd"])


def test_run_path_nonexistent():
    result = nox.command.run(
        [PYTHON, "-c", "import sys; print(sys.executable)"],
        silent=True,
        path="/non/existent",
    )

    assert "/non/existent" not in result


def test_run_path_existent(tmpdir, monkeypatch):
    executable = tmpdir.join("testexc")
    executable.ensure("")
    executable.chmod(0o700)

    with mock.patch("nox.command.popen") as mock_command:
        mock_command.return_value = (0, "")
        nox.command.run(["testexc"], silent=True, path=tmpdir.strpath)
        mock_command.assert_called_with([executable.strpath], env=None, silent=True)


def test_run_external_warns(tmpdir, caplog):
    caplog.set_level(logging.WARNING)

    nox.command.run([PYTHON, "--version"], silent=True, path=tmpdir.strpath)

    assert "external=True" in caplog.text


def test_run_external_silences(tmpdir, caplog):
    caplog.set_level(logging.WARNING)

    nox.command.run(
        [PYTHON, "--version"], silent=True, path=tmpdir.strpath, external=True
    )

    assert "external=True" not in caplog.text


def test_run_external_raises(tmpdir, caplog):
    caplog.set_level(logging.ERROR)

    with pytest.raises(nox.command.CommandFailed):
        nox.command.run(
            [PYTHON, "--version"], silent=True, path=tmpdir.strpath, external="error"
        )

    assert "external=True" in caplog.text


def test_exit_codes():
    assert nox.command.run([PYTHON, "-c", "import sys; sys.exit(0)"])

    with pytest.raises(nox.command.CommandFailed):
        nox.command.run([PYTHON, "-c", "import sys; sys.exit(1)"])

    assert nox.command.run(
        [PYTHON, "-c", "import sys; sys.exit(1)"], success_codes=[1, 2]
    )


def test_fail_with_silent(capsys):
    with pytest.raises(nox.command.CommandFailed):
        nox.command.run(
            [
                PYTHON,
                "-c",
                'import sys; sys.stdout.write("out");'
                'sys.stderr.write("err"); sys.exit(1)',
            ],
            silent=True,
        )
        out, err = capsys.readouterr()
        assert "out" in err
        assert "err" in err


def test_interrupt():
    mock_proc = mock.Mock()
    mock_proc.communicate.side_effect = KeyboardInterrupt()

    with mock.patch("subprocess.Popen", return_value=mock_proc):
        with pytest.raises(KeyboardInterrupt):
            nox.command.run([PYTHON, "-c" "123"])
