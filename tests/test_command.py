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

import nox.command
import nox.popen
import pytest

PYTHON = sys.executable


def test_run_defaults(capsys):
    result = nox.command.run([PYTHON, "-c", "print(123)"])

    assert result is True


def test_run_silent(capsys):
    result = nox.command.run([PYTHON, "-c", "print(123)"], silent=True)

    out, _ = capsys.readouterr()

    assert "123" in result
    assert out == ""


def test_run_verbosity(capsys, caplog):
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        result = nox.command.run([PYTHON, "-c", "print(123)"], silent=True)

        out, _ = capsys.readouterr()

        assert "123" in result
        assert out == ""

    logs = [rec for rec in caplog.records if rec.levelname == "OUTPUT"]
    assert not logs

    caplog.clear()
    with caplog.at_level(logging.DEBUG - 1):
        result = nox.command.run([PYTHON, "-c", "print(123)"], silent=True)

        out, _ = capsys.readouterr()

        assert "123" in result
        assert out == ""

    logs = [rec for rec in caplog.records if rec.levelname == "OUTPUT"]
    assert logs
    assert logs[0].message.strip() == "123"


def test_run_verbosity_failed_command(capsys, caplog):
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(nox.command.CommandFailed):
            nox.command.run([PYTHON, "-c", "print(123); exit(1)"], silent=True)

        out, err = capsys.readouterr()

        assert "123" in err
        assert out == ""

    logs = [rec for rec in caplog.records if rec.levelname == "OUTPUT"]
    assert not logs

    caplog.clear()
    with caplog.at_level(logging.DEBUG - 1):
        with pytest.raises(nox.command.CommandFailed):
            nox.command.run([PYTHON, "-c", "print(123); exit(1)"], silent=True)

        out, err = capsys.readouterr()

        assert "123" in err
        assert out == ""

    # Nothing is logged but the error is still written to stderr
    assert not logs


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
        paths=["/non/existent"],
    )

    assert "/non/existent" not in result


def test_run_path_existent(tmpdir, monkeypatch):
    executable = tmpdir.join("testexc")
    executable.ensure("")
    executable.chmod(0o700)

    with mock.patch("nox.command.popen") as mock_command:
        mock_command.return_value = (0, "")
        nox.command.run(["testexc"], silent=True, paths=[tmpdir.strpath])
        mock_command.assert_called_with([executable.strpath], env=None, silent=True)


def test_run_external_warns(tmpdir, caplog):
    caplog.set_level(logging.WARNING)

    nox.command.run([PYTHON, "--version"], silent=True, paths=[tmpdir.strpath])

    assert "external=True" in caplog.text


def test_run_external_silences(tmpdir, caplog):
    caplog.set_level(logging.WARNING)

    nox.command.run(
        [PYTHON, "--version"], silent=True, paths=[tmpdir.strpath], external=True
    )

    assert "external=True" not in caplog.text


def test_run_external_raises(tmpdir, caplog):
    caplog.set_level(logging.ERROR)

    with pytest.raises(nox.command.CommandFailed):
        nox.command.run(
            [PYTHON, "--version"], silent=True, paths=[tmpdir.strpath], external="error"
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


def test_custom_stdout(capsys, tmpdir):
    with open(str(tmpdir / "out.txt"), "w+b") as stdout:
        nox.command.run(
            [
                PYTHON,
                "-c",
                'import sys; sys.stdout.write("out");'
                'sys.stderr.write("err"); sys.exit(0)',
            ],
            stdout=stdout,
        )
        out, err = capsys.readouterr()
        assert not out
        assert "out" not in err
        assert "err" not in err
        stdout.seek(0)
        tempfile_contents = stdout.read().decode("utf-8")
        assert "out" in tempfile_contents
        assert "err" in tempfile_contents


def test_custom_stdout_silent_flag(capsys, tmpdir):
    with open(str(tmpdir / "out.txt"), "w+b") as stdout:
        with pytest.raises(ValueError, match="silent"):
            nox.command.run([PYTHON, "-c", 'print("hi")'], stdout=stdout, silent=True)


def test_custom_stdout_failed_command(capsys, tmpdir):
    with open(str(tmpdir / "out.txt"), "w+b") as stdout:
        with pytest.raises(nox.command.CommandFailed):
            nox.command.run(
                [
                    PYTHON,
                    "-c",
                    'import sys; sys.stdout.write("out");'
                    'sys.stderr.write("err"); sys.exit(1)',
                ],
                stdout=stdout,
            )
        out, err = capsys.readouterr()
        assert not out
        assert "out" not in err
        assert "err" not in err
        stdout.seek(0)
        tempfile_contents = stdout.read().decode("utf-8")
        assert "out" in tempfile_contents
        assert "err" in tempfile_contents


def test_custom_stderr(capsys, tmpdir):
    with open(str(tmpdir / "err.txt"), "w+b") as stderr:
        nox.command.run(
            [
                PYTHON,
                "-c",
                'import sys; sys.stdout.write("out");'
                'sys.stderr.write("err"); sys.exit(0)',
            ],
            stderr=stderr,
        )
        out, err = capsys.readouterr()
        assert not err
        assert "out" not in out
        assert "err" not in out
        stderr.seek(0)
        tempfile_contents = stderr.read().decode("utf-8")
        assert "out" not in tempfile_contents
        assert "err" in tempfile_contents


def test_custom_stderr_failed_command(capsys, tmpdir):
    with open(str(tmpdir / "out.txt"), "w+b") as stderr:
        with pytest.raises(nox.command.CommandFailed):
            nox.command.run(
                [
                    PYTHON,
                    "-c",
                    'import sys; sys.stdout.write("out");'
                    'sys.stderr.write("err"); sys.exit(1)',
                ],
                stderr=stderr,
            )
        out, err = capsys.readouterr()
        assert not err
        assert "out" not in out
        assert "err" not in out
        stderr.seek(0)
        tempfile_contents = stderr.read().decode("utf-8")
        assert "out" not in tempfile_contents
        assert "err" in tempfile_contents


def test_output_decoding() -> None:
    result = nox.popen.decode_output(b"abc")

    assert result == "abc"


def test_output_decoding_non_ascii() -> None:
    result = nox.popen.decode_output("ü".encode("utf-8"))

    assert result == "ü"


def test_output_decoding_utf8_only_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox.popen.locale, "getpreferredencoding", lambda: "utf8")

    with pytest.raises(UnicodeDecodeError) as exc:
        nox.popen.decode_output(b"\x95")

    assert exc.value.encoding == "utf-8"


def test_output_decoding_utf8_fail_cp1252_success(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(nox.popen.locale, "getpreferredencoding", lambda: "cp1252")

    result = nox.popen.decode_output(b"\x95")

    assert result == "•"  # U+2022


def test_output_decoding_both_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox.popen.locale, "getpreferredencoding", lambda: "ascii")

    with pytest.raises(UnicodeDecodeError) as exc:
        nox.popen.decode_output(b"\x95")

    assert exc.value.encoding == "ascii"
