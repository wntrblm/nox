# Copyright 2026 Nox contributors
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

import asyncio
import sys
from typing import TYPE_CHECKING, Any

import pytest

from nox.popen import _ASYNCIO_LINE_LENGTH_LIMIT, _TeeSubprocess, tee_popen

if TYPE_CHECKING:
    from pathlib import Path

PYTHON = sys.executable


TEE_POPEN_DATA: list[tuple[list[str], dict[str, Any], int, str, str, list[str]]] = [
    (
        [
            PYTHON,
            "-c",
            (
                'import sys; sys.stdout.write("out");'
                'sys.stderr.write("err"); sys.exit(42)'
            ),
        ],
        {},
        42,
        "out",
        "err",
        ["errout", "outerr"],
    ),
    (
        [
            PYTHON,
            "-c",
            (
                'import sys; import os; sys.stdout.write(os.environ["FOO"]);'
                'sys.stderr.write(os.getenv("BAR", "<none>"))'
            ),
        ],
        {
            "env": {"FOO": "1234bar"},
        },
        0,
        "1234bar",
        "<none>",
        ["<none>1234bar", "1234bar<none>"],
    ),
    (
        [
            PYTHON,
            "-c",
            (
                'import sys; print("1", file=sys.stdout); print("2", file=sys.stderr);'
                'print("3", file=sys.stdout);'
            ),
        ],
        {},
        0,
        "1\n3\n",
        "2\n",
        ["2\n1\n3\n", "1\n2\n3\n", "1\n3\n2\n"],
    ),
]


@pytest.mark.parametrize(
    (
        "command",
        "kwargs",
        "expected_exit_code",
        "expected_out",
        "expected_err",
        "expected_captured_out",
    ),
    TEE_POPEN_DATA,
)
def test_tee_popen(
    command: list[str],
    kwargs: dict[str, Any],
    expected_exit_code: int,
    expected_out: str,
    expected_err: str,
    expected_captured_out: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, stdout, stderr = tee_popen(command, **kwargs)

    assert exit_code == expected_exit_code
    assert stdout == expected_out
    assert stderr == expected_err

    captured = capsys.readouterr()
    assert captured.out in expected_captured_out
    assert captured.err == ""


def test_tee_popen_long_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    repeat = _ASYNCIO_LINE_LENGTH_LIMIT + 10
    exit_code, stdout, stderr = tee_popen(
        [
            PYTHON,
            "-c",
            f'import sys; print("1" * {repeat})',
        ]
    )

    expected = "1" * repeat + "\n"

    assert exit_code == 0
    assert stdout == expected
    assert stderr == ""

    captured = capsys.readouterr()
    assert captured.out == expected
    assert captured.err == ""


def test__TeeSubprocess_interrupt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    teesub = _TeeSubprocess(
        interrupt_timeout=0,
        terminate_timeout=0,
    )

    async def term() -> None:
        # The delay should be long enough so that the Python subprocess
        # has time to start running and print the first output.
        await asyncio.sleep(0.5)
        teesub._handle_sigint()
        teesub._handle_sigint()  # calling it twice should be handled

    with pytest.raises(KeyboardInterrupt):
        teesub.run(
            [
                PYTHON,
                "-c",
                (
                    'import sys; import time; print("1"); sys.stdout.flush(); time.sleep(10); print("2");'
                ),
            ],
            extra_tasks=[teesub.loop.create_task(term())],
        )

    captured = capsys.readouterr()
    assert captured.out == "1\n"
    assert captured.err == ""


def test__TeeSubprocess_interrupt_wait(
    capsys: pytest.CaptureFixture[str],
) -> None:
    teesub = _TeeSubprocess(
        interrupt_timeout=0,
        terminate_timeout=1,
    )

    async def term() -> None:
        # The delay should be long enough so that the Python subprocess
        # has time to start running and print the first output.
        await asyncio.sleep(0.25)
        teesub._handle_sigint()
        teesub._handle_sigint()  # calling it twice should be handled

    with pytest.raises(KeyboardInterrupt):
        teesub.run(
            [
                PYTHON,
                "-c",
                (
                    'import sys; import time; print("1"); sys.stdout.flush(); time.sleep(10); print("2");'
                ),
            ],
            extra_tasks=[teesub.loop.create_task(term())],
        )

    captured = capsys.readouterr()
    assert captured.out == "1\n"
    assert captured.err == ""


def test__TeeSubprocess_graceful_shutdown(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    program = tmp_path / "run.py"
    program.write_text(
        r"""
import signal
import sys
import time

def handler(signum, frame):
    print(f"Signal handler called with signal {signum}")
    sys.stdout.flush()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

print("1")
sys.stdout.flush()
time.sleep(1)
print("2")
sys.stdout.flush()
time.sleep(0.5)
print("3")
sys.stdout.flush()
time.sleep(10)
print("4")
""",
        encoding="utf-8",
    )
    teesub = _TeeSubprocess(
        interrupt_timeout=0.5,
        terminate_timeout=0.5,
    )

    async def term() -> None:
        # The delay should be long enough so that the Python subprocess
        # has time to start running and print the first output.
        await asyncio.sleep(0.25)
        teesub._handle_sigint()

    with pytest.raises(KeyboardInterrupt):
        teesub.run(
            [PYTHON, str(program)],
            extra_tasks=[teesub.loop.create_task(term())],
        )

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        # We don't see SIGINT here since we don't send that signal to the process.
        "1",
        "Signal handler called with signal 15",
        "2",
    ]
    assert captured.err == ""


def test__TeeSubprocess_shutdown_finish_in_time(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    program = tmp_path / "run.py"
    program.write_text(
        r"""
import signal
import sys
import time

def handler(signum, frame):
    print(f"Signal handler called with signal {signum}")
    sys.stdout.flush()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

print("1")
sys.stdout.flush()
time.sleep(0.3)
print("2")
""",
        encoding="utf-8",
    )
    teesub = _TeeSubprocess(
        interrupt_timeout=0.5,
        terminate_timeout=0,
    )

    async def term() -> None:
        # The delay should be long enough so that the Python subprocess
        # has time to start running and print the first output.
        await asyncio.sleep(0.1)
        teesub._handle_sigint()

    # The program exits fast enough, so no KeyboardInterrupt is re-raised.
    exit_code, stdout, stderr = teesub.run(
        [PYTHON, str(program)],
        extra_tasks=[teesub.loop.create_task(term())],
    )

    assert exit_code == 0
    assert stdout == b"1\n2\n"
    assert stderr == b""

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "1",
        "2",
    ]
    assert captured.err == ""


def test__TeeSubprocess_shutdown_terminate_in_time(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    program = tmp_path / "run.py"
    program.write_text(
        r"""
import signal
import sys
import time

def handler(signum, frame):
    print(f"Signal handler called with signal {signum}")
    sys.stdout.flush()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

print("1")
sys.stdout.flush()
time.sleep(0.5)
print("2")
""",
        encoding="utf-8",
    )
    teesub = _TeeSubprocess(
        interrupt_timeout=0.2,
        terminate_timeout=0.5,
    )

    async def term() -> None:
        # The delay should be long enough so that the Python subprocess
        # has time to start running and print the first output.
        await asyncio.sleep(0.1)
        teesub._handle_sigint()

    # The program exits fast enough, so no KeyboardInterrupt is re-raised.
    exit_code, stdout, stderr = teesub.run(
        [PYTHON, str(program)],
        extra_tasks=[teesub.loop.create_task(term())],
    )

    assert exit_code == 0
    assert stdout == b"1\nSignal handler called with signal 15\n2\n"
    assert stderr == b""

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "1",
        "Signal handler called with signal 15",
        "2",
    ]
    assert captured.err == ""


def test__TeeSubprocess_shutdown_kill(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    program = tmp_path / "run.py"
    program.write_text(
        r"""
import signal
import sys
import time

def handler(signum, frame):
    print(f"Signal handler called with signal {signum}")
    sys.stdout.flush()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

print("1")
sys.stdout.flush()
time.sleep(0.5)
print("2")
sys.stdout.flush()
time.sleep(0.5)
print("3")
sys.stdout.flush()
time.sleep(10)
print("4")
""",
        encoding="utf-8",
    )
    teesub = _TeeSubprocess(
        interrupt_timeout=0.2,
        terminate_timeout=0.5,
    )

    async def term() -> None:
        # The delay should be long enough so that the Python subprocess
        # has time to start running and print the first output.
        await asyncio.sleep(0.1)
        teesub._handle_sigint()

    with pytest.raises(KeyboardInterrupt):
        teesub.run(
            [PYTHON, str(program)],
            extra_tasks=[teesub.loop.create_task(term())],
        )

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "1",
        "Signal handler called with signal 15",
        "2",
    ]
    assert captured.err == ""


def test__TeeSubprocess_shutdown_interrupt_before_start() -> None:
    teesub = _TeeSubprocess(
        interrupt_timeout=0,
        terminate_timeout=0,
    )

    assert teesub.do_terminate is False
    assert teesub.is_terminating is False

    # Calling this before run() simulates that a KeyboardInterrupt
    # is triggered after creating the _TeeSubprocess() object and
    # before creating its main_task.
    teesub._handle_sigint()

    assert teesub.do_terminate is True
    # I have no idea why mypy thinks that the next line is unreachable...
    assert teesub.is_terminating is False  # type: ignore[unreachable]

    # The program exits fast enough, so no KeyboardInterrupt is re-raised.
    with pytest.raises(KeyboardInterrupt):
        teesub.run(
            [PYTHON, "-c", 'print("1")'],
        )
