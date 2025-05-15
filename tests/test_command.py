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

import ctypes
import logging
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from textwrap import dedent
from typing import Any
from unittest import mock

import pytest

import nox.command
import nox.popen

PYTHON = sys.executable

skip_on_windows_primary_console_session = pytest.mark.skipif(
    sys.platform.startswith("win") and "SECONDARY_CONSOLE_SESSION" not in os.environ,
    reason="On Windows, this test must run in a separate console session.",
)

only_on_windows = pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="Only run this test on Windows."
)


def test_run_defaults() -> None:
    result = nox.command.run([PYTHON, "-c", "print(123)"])

    assert result is True


def test_run_silent(capsys: pytest.CaptureFixture[str]) -> None:
    result = nox.command.run([PYTHON, "-c", "print(123)"], silent=True)

    out, _ = capsys.readouterr()

    assert "123" in result
    assert out == ""


@pytest.mark.skipif(shutil.which("git") is None, reason="Needs git")
def test_run_not_in_path() -> None:
    # Paths falls back on the environment PATH if the command is not found.
    result = nox.command.run(["git", "--version"], paths=["."])
    assert result is True


def test_run_verbosity(
    capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
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


def test_run_verbosity_failed_command(caplog: pytest.LogCaptureFixture) -> None:
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(nox.command.CommandFailed):
            nox.command.run([PYTHON, "-c", "print(123); exit(1)"], silent=True)

        assert "123" in caplog.text

    logs = [rec for rec in caplog.records if rec.levelname == "OUTPUT"]
    assert not logs

    caplog.clear()
    with caplog.at_level(logging.DEBUG - 1):
        with pytest.raises(nox.command.CommandFailed):
            nox.command.run([PYTHON, "-c", "print(123); exit(1)"], silent=True)

        assert "123" in caplog.text

    # Nothing is logged but the error is still written to stderr
    assert not logs


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="See https://github.com/python/cpython/issues/85815",
)
def test_run_non_str() -> None:
    result = nox.command.run(
        [Path(PYTHON), "-c", "import sys; print(sys.argv)", Path(PYTHON)],
        silent=True,
    )

    assert PYTHON in result


def test_run_env_unicode() -> None:
    result = nox.command.run(
        [PYTHON, "-c", 'import os; print(os.environ["SIGIL"])'],
        silent=True,
        env={"SIGIL": "123"},
    )

    assert "123" in result


def test_run_env_remove(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMPTY", "notempty")
    nox.command.run(
        [PYTHON, "-c", 'import os; assert "EMPTY" in os.environ'],
        silent=True,
    )
    nox.command.run(
        [PYTHON, "-c", 'import os; assert "EMPTY" not in os.environ'],
        silent=True,
        env={"EMPTY": None},
    )


@mock.patch("nox.command._PLATFORM", "win32")
def test_run_env_systemroot() -> None:
    systemroot = os.environ.setdefault("SYSTEMROOT", "sigil")

    result = nox.command.run(
        [PYTHON, "-c", 'import os; print(os.environ["SYSTEMROOT"])'], silent=True
    )

    assert systemroot in result


def test_run_not_found() -> None:
    with pytest.raises(nox.command.CommandFailed):
        nox.command.run(["nonexistentcmd"])


def test_run_path_nonexistent() -> None:
    result = nox.command.run(
        [PYTHON, "-c", "import sys; print(sys.executable)"],
        silent=True,
        paths=["/non/existent"],
    )

    assert "/non/existent" not in result


def test_run_path_existent(tmp_path: Path) -> None:
    executable_name = (
        "testexc.exe" if "windows" in platform.platform().lower() else "testexc"
    )
    tmp_path.touch()
    executable = tmp_path.joinpath(executable_name)
    executable.touch()
    executable.chmod(0o700)

    with mock.patch("nox.command.popen") as mock_command:
        mock_command.return_value = (0, "")
        nox.command.run([executable_name], silent=True, paths=[str(tmp_path)])
        mock_command.assert_called_with(
            [str(executable)],
            env=None,
            silent=True,
            stdout=None,
            stderr=subprocess.STDOUT,
            interrupt_timeout=0.3,
            terminate_timeout=0.2,
        )


def test_run_external_warns(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)

    nox.command.run([PYTHON, "--version"], silent=True, paths=[tmp_path])

    assert "external=True" in caplog.text


def test_run_external_silences(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)

    nox.command.run([PYTHON, "--version"], silent=True, paths=[tmp_path], external=True)

    assert "external=True" not in caplog.text


def test_run_external_raises(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)

    with pytest.raises(nox.command.CommandFailed):
        nox.command.run(
            [PYTHON, "--version"], silent=True, paths=[tmp_path], external="error"
        )

    assert "external=True" in caplog.text


def test_exit_codes() -> None:
    assert nox.command.run([PYTHON, "-c", "import sys; sys.exit(0)"])

    with pytest.raises(nox.command.CommandFailed):
        nox.command.run([PYTHON, "-c", "import sys; sys.exit(1)"])

    assert nox.command.run(
        [PYTHON, "-c", "import sys; sys.exit(1)"], success_codes=[1, 2]
    )


def test_fail_with_silent(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    caplog.clear()
    with pytest.raises(nox.command.CommandFailed):
        nox.command.run(
            [
                PYTHON,
                "-c",
                (
                    'import sys; sys.stdout.write("out");'
                    'sys.stderr.write("err"); sys.exit(1)'
                ),
            ],
            silent=True,
        )
    out, err = capsys.readouterr()
    assert "out" not in err
    assert "err" not in err
    assert "out" in caplog.text
    assert "err" in caplog.text


@pytest.fixture
def marker(tmp_path: Path) -> Path:
    """A marker file for process communication."""
    return tmp_path / "marker"


def enable_ctrl_c(*, enabled: bool) -> None:
    """Enable keyboard interrupts (CTRL-C) on Windows."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]

    if not kernel32.SetConsoleCtrlHandler(None, not enabled):
        raise ctypes.WinError(ctypes.get_last_error())  # type: ignore[attr-defined]


def interrupt_process(proc: subprocess.Popen[Any]) -> None:
    """Send SIGINT or CTRL_C_EVENT to the process."""
    if sys.platform.startswith("win"):
        # Disable Ctrl-C so we don't terminate ourselves.
        enable_ctrl_c(enabled=False)

        # Send the keyboard interrupt to all processes attached to the current
        # console session.
        os.kill(0, signal.CTRL_C_EVENT)  # type: ignore[attr-defined]
    else:
        proc.send_signal(signal.SIGINT)


@pytest.fixture
def command_with_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch, marker: Any
) -> None:
    """Monkeypatch Popen.communicate to raise KeyboardInterrupt."""
    if sys.platform.startswith("win"):
        # Enable Ctrl-C because the child inherits the setting from us.
        enable_ctrl_c(enabled=True)

    communicate = subprocess.Popen.communicate

    def wrapper(
        proc: subprocess.Popen[Any], *args: Any, **kwargs: Any
    ) -> tuple[Any, Any]:
        # Raise the interrupt only on the first call, so Nox has a chance to
        # shut down the child process subsequently.

        if wrapper.firstcall:  # type: ignore[attr-defined]
            wrapper.firstcall = False  # type: ignore[attr-defined]

            # Give the child time to install its signal handlers.
            while not marker.exists():
                time.sleep(0.05)

            # Send a real keyboard interrupt to the child.
            interrupt_process(proc)

            # Fake a keyboard interrupt in the parent.
            raise KeyboardInterrupt

        return communicate(proc, *args, **kwargs)

    wrapper.firstcall = True  # type: ignore[attr-defined]

    monkeypatch.setattr("subprocess.Popen.communicate", wrapper)


def format_program(program: str, marker: Any) -> str:
    """Preprocess the Python program run by the child process."""
    main = f"""
    import time
    from pathlib import Path

    Path({str(marker)!r}).touch()
    time.sleep(3)
    """
    return dedent(program).format(MAIN=dedent(main))


def run_pytest_in_new_console_session(test: str) -> None:
    """Run the given test in a separate console session."""
    env = dict(os.environ, SECONDARY_CONSOLE_SESSION="")
    creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    subprocess.run(
        [sys.executable, "-m", "pytest", f"{__file__}::{test}"],
        env=env,
        check=True,
        capture_output=True,
        creationflags=creationflags,
    )


@skip_on_windows_primary_console_session
@pytest.mark.parametrize(
    "program",
    [
        """
        {MAIN}
        """,
        """
        import signal

        signal.signal(signal.SIGINT, signal.SIG_IGN)

        {MAIN}
        """,
        """
        import signal

        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

        {MAIN}
        """,
    ],
)
@pytest.mark.usefixtures("command_with_keyboard_interrupt")
def test_interrupt_raises(
    program: str,
    marker: Any,
) -> None:
    """It kills the process and reraises the keyboard interrupt."""
    with pytest.raises(KeyboardInterrupt):
        nox.command.run([PYTHON, "-c", format_program(program, marker)])


@only_on_windows
def test_interrupt_raises_on_windows() -> None:
    """It kills the process and reraises the keyboard interrupt."""
    run_pytest_in_new_console_session("test_interrupt_raises")


@skip_on_windows_primary_console_session
def test_interrupt_handled(command_with_keyboard_interrupt: None, marker: Any) -> None:  # noqa: ARG001
    """It does not raise if the child handles the keyboard interrupt."""
    program = """
    import signal

    def exithandler(sig, frame):
        raise SystemExit()

    signal.signal(signal.SIGINT, exithandler)

    {MAIN}
    """
    nox.command.run([PYTHON, "-c", format_program(program, marker)])


@only_on_windows
def test_interrupt_handled_on_windows() -> None:
    """It does not raise if the child handles the keyboard interrupt."""
    run_pytest_in_new_console_session("test_interrupt_handled")


def test_custom_stdout(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    with (tmp_path / "out.txt").open("w+", encoding="utf-8") as stdout:
        nox.command.run(
            [
                PYTHON,
                "-c",
                (
                    'import sys; sys.stdout.write("out");'
                    'sys.stderr.write("err"); sys.exit(0)'
                ),
            ],
            stdout=stdout,
        )
        out, err = capsys.readouterr()
        assert not out
        assert "out" not in err
        assert "err" not in err
        stdout.seek(0)
        tempfile_contents = stdout.read()
        assert "out" in tempfile_contents
        assert "err" in tempfile_contents


def test_custom_stdout_silent_flag(tmp_path: Path) -> None:
    with (tmp_path / "out.txt").open("w+", encoding="utf-8") as stdout:  # noqa: SIM117
        with pytest.raises(ValueError, match="silent"):
            nox.command.run([PYTHON, "-c", 'print("hi")'], stdout=stdout, silent=True)


def test_custom_stdout_failed_command(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    with (tmp_path / "out.txt").open("w+", encoding="utf-8") as stdout:
        with pytest.raises(nox.command.CommandFailed):
            nox.command.run(
                [
                    PYTHON,
                    "-c",
                    (
                        'import sys; sys.stdout.write("out");'
                        'sys.stderr.write("err"); sys.exit(1)'
                    ),
                ],
                stdout=stdout,
            )
        out, err = capsys.readouterr()
        assert not out
        assert "out" not in err
        assert "err" not in err
        stdout.seek(0)
        tempfile_contents = stdout.read()
        assert "out" in tempfile_contents
        assert "err" in tempfile_contents


def test_custom_stderr(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    with (tmp_path / "err.txt").open("w+", encoding="utf-8") as stderr:
        nox.command.run(
            [
                PYTHON,
                "-c",
                (
                    'import sys; sys.stdout.write("out");'
                    'sys.stderr.write("err"); sys.exit(0)'
                ),
            ],
            stderr=stderr,
        )
        out, err = capsys.readouterr()
        assert not err
        assert "out" not in out
        assert "err" not in out
        stderr.seek(0)
        tempfile_contents = stderr.read()
        assert "out" not in tempfile_contents
        assert "err" in tempfile_contents


def test_custom_stderr_failed_command(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    with (tmp_path / "out.txt").open("w+", encoding="utf-8") as stderr:
        with pytest.raises(nox.command.CommandFailed):
            nox.command.run(
                [
                    PYTHON,
                    "-c",
                    (
                        'import sys; sys.stdout.write("out");'
                        'sys.stderr.write("err"); sys.exit(1)'
                    ),
                ],
                stderr=stderr,
            )
        out, err = capsys.readouterr()
        assert not err
        assert "out" not in out
        assert "err" not in out
        stderr.seek(0)
        tempfile_contents = stderr.read()
        assert "out" not in tempfile_contents
        assert "err" in tempfile_contents


def test_output_decoding() -> None:
    result = nox.popen.decode_output(b"abc")

    assert result == "abc"


def test_output_decoding_non_ascii() -> None:
    result = nox.popen.decode_output("ü".encode())

    assert result == "ü"


def test_output_decoding_utf8_only_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox.popen.locale, "getpreferredencoding", lambda: "utf8")  # type: ignore[attr-defined]

    with pytest.raises(UnicodeDecodeError) as exc:
        nox.popen.decode_output(b"\x95")

    assert exc.value.encoding == "utf-8"


def test_output_decoding_utf8_fail_cp1252_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nox.popen.locale, "getpreferredencoding", lambda: "cp1252")  # type: ignore[attr-defined]

    result = nox.popen.decode_output(b"\x95")

    assert result == "•"  # U+2022


def test_output_decoding_both_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox.popen.locale, "getpreferredencoding", lambda: "ascii")  # type: ignore[attr-defined]

    with pytest.raises(UnicodeDecodeError) as exc:
        nox.popen.decode_output(b"\x95")

    assert exc.value.encoding == "ascii"
