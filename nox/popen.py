# Copyright 2017 Alethea Katherine Flowers
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

__lazy_modules__ = {"asyncio", "contextlib", "itertools", "locale", "signal"}

import asyncio
import contextlib
import itertools
import locale
import os
import signal
import subprocess
import sys
from typing import IO, TYPE_CHECKING, BinaryIO, Literal, overload

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from collections.abc import Mapping, Sequence

__all__ = [
    "DEFAULT_INTERRUPT_TIMEOUT",
    "DEFAULT_TERMINATE_TIMEOUT",
    "decode_output",
    "popen",
    "tee_popen",
]


def __dir__() -> list[str]:
    return __all__


DEFAULT_INTERRUPT_TIMEOUT = 0.3
DEFAULT_TERMINATE_TIMEOUT = 0.2

_CMD_META = frozenset("&<>^|()")

# Variables cmd.exe resolves dynamically or defines itself, so a reference to
# one expands even when it is absent from the child process environment.
_CMD_AUTO_VARS = frozenset(
    {
        "__APPDIR__",
        "__CD__",
        "CD",
        "CMDCMDLINE",
        "CMDEXTVERSION",
        "COMSPEC",
        "DATE",
        "ERRORLEVEL",
        "HIGHESTNUMANODENUMBER",
        "PATHEXT",
        "PROMPT",
        "RANDOM",
        "TIME",
    }
)


def _expandable_reference(arg: str, env: Mapping[str, str]) -> str | None:
    """Find a ``%VAR%`` reference that cmd.exe would expand, if there is one.

    cmd.exe scans the text between each pair of ``%`` characters; when it
    names a defined (or dynamic) variable - optionally followed by ``:``
    modifiers, the value is substituted, even inside double quotes. An
    undefined name is left alone and the scan resumes at the trailing ``%``.
    """
    defined = {name.upper() for name in env}
    percents = [index for index, char in enumerate(arg) if char == "%"]
    for start, end in itertools.pairwise(percents):
        name = arg[start + 1 : end].partition(":")[0].upper()
        if name and (
            name in defined
            or name in _CMD_AUTO_VARS
            # hidden variables such as the per-drive working directory "=C:"
            or name.startswith("=")
        ):
            return arg[start : end + 1]
    return None


def _windows_batch_command(
    args: Sequence[str], env: Mapping[str, str] | None = None
) -> str:
    """Build a command line that protects the cmd.exe metacharacters ``&<>^|()``.

    Arguments cmd.exe would corrupt anyway are rejected: ``%VAR%`` references
    are expanded even inside double quotes, and quote characters cannot be
    escaped. cmd.exe doesn't have backslash escapes, it only counts quotes.
    """
    if env is None:
        env = os.environ

    quoted_args = []
    for arg in args:
        reference = _expandable_reference(arg, env)
        if reference is not None:
            msg = (
                "Cannot escape argument for batch script, cmd.exe would"
                f" expand {reference}: {arg}"
            )
            raise ValueError(msg)
        if _CMD_META.isdisjoint(arg):
            quoted_args.append(subprocess.list2cmdline([arg]))
        elif len(arg) >= 2 and arg[0] == arg[-1] == '"' and '"' not in arg[1:-1]:
            # A pre-quoted argument such as '"urllib3<1.25"' (the historical
            # workaround): its outer quotes already protect the
            # metacharacters, so pass it through unchanged.
            quoted_args.append(arg)
        elif '"' in arg:
            # list2cmdline escapes embedded quotes with backslashes, but
            # cmd.exe doesn't have backslash escapes.
            msg = f"Cannot escape argument for batch script: {arg}"
            raise ValueError(msg)
        else:
            # Force list2cmdline to quote the argument, then remove the
            # temporary leading space without changing the argument itself:
            # ' requests<99' -> '" requests<99"' -> '"requests<99"'
            quoted = subprocess.list2cmdline([f" {arg}"])
            quoted_args.append(f"{quoted[0]}{quoted[2:]}")
    return " ".join(quoted_args)


def shutdown_process(
    proc: subprocess.Popen[bytes],
    interrupt_timeout: float | None,
    terminate_timeout: float | None,
) -> tuple[bytes, bytes]:
    """Gracefully shutdown a child process."""
    with contextlib.suppress(subprocess.TimeoutExpired):
        return proc.communicate(timeout=interrupt_timeout)

    proc.terminate()

    with contextlib.suppress(subprocess.TimeoutExpired):
        return proc.communicate(timeout=terminate_timeout)

    proc.kill()

    return proc.communicate()


def decode_output(output: bytes) -> str:
    """Try to decode the given bytes with encodings from the system.

    :param output: output to decode
    :raises UnicodeDecodeError: if all encodings fail
    :return: decoded string
    """
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError:
        second_encoding = locale.getpreferredencoding()
        if second_encoding.casefold() in {"utf8", "utf-8"}:
            raise

        return output.decode(second_encoding)


@overload
def popen(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = ...,
    silent: bool = ...,
    return_stderr: Literal[False] = ...,
    stdout: int | IO[str] | None = ...,
    stderr: int | IO[str] | None = ...,
    interrupt_timeout: float | None = ...,
    terminate_timeout: float | None = ...,
) -> tuple[int, str]: ...


@overload
def popen(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = ...,
    silent: bool = ...,
    return_stderr: Literal[True],
    stdout: int | IO[str] | None = ...,
    stderr: int | IO[str] | None = ...,
    interrupt_timeout: float | None = ...,
    terminate_timeout: float | None = ...,
) -> tuple[int, str, str]: ...


@overload
def popen(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = ...,
    silent: bool = ...,
    return_stderr: bool = ...,
    stdout: int | IO[str] | None = ...,
    stderr: int | IO[str] | None = ...,
    interrupt_timeout: float | None = ...,
    terminate_timeout: float | None = ...,
) -> tuple[int, str] | tuple[int, str, str]: ...


def popen(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    silent: bool = False,
    return_stderr: bool = False,
    stdout: int | IO[str] | None = None,
    stderr: int | IO[str] | None = subprocess.STDOUT,
    interrupt_timeout: float | None = DEFAULT_INTERRUPT_TIMEOUT,
    terminate_timeout: float | None = DEFAULT_TERMINATE_TIMEOUT,
) -> tuple[int, str] | tuple[int, str, str]:
    if silent and stdout is not None:
        msg = (
            "Can not specify silent and stdout; passing a custom stdout always silences"
            " the commands output in Nox's log."
        )
        raise ValueError(msg)

    if silent:
        stdout = subprocess.PIPE

    popen_args: Sequence[str] | str = args
    if sys.platform.startswith("win") and args[0].casefold().endswith((".bat", ".cmd")):
        popen_args = _windows_batch_command(args, env)

    proc = subprocess.Popen(popen_args, env=env, stdout=stdout, stderr=stderr)

    try:
        out, err = proc.communicate()
        sys.stdout.flush()

    except KeyboardInterrupt:
        out, err = shutdown_process(proc, interrupt_timeout, terminate_timeout)
        if proc.returncode != 0:
            raise

    return_code = proc.wait()

    ret_out = decode_output(out) if out else ""
    if not return_stderr:
        return return_code, ret_out
    return return_code, ret_out, decode_output(err) if err else ""


_ASYNCIO_LINE_LENGTH_LIMIT = 2**23  # Increase line length limit to 8 MiB


class _TeeSubprocess:
    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        interrupt_timeout: float | None,
        terminate_timeout: float | None,
    ) -> None:
        self.loop = loop
        self.stdout: list[bytes] = []
        self.stderr: list[bytes] = []
        self.interrupt_timeout = interrupt_timeout
        self.terminate_timeout = terminate_timeout
        self.collectors: list[asyncio.Task[None] | asyncio.Task[int]] = []
        self.main_task: asyncio.Task[bool] | None = None

    async def _shutdown_process(self, proc: Process) -> None:
        """Gracefully shutdown a child process."""
        _, pending = await asyncio.wait(self.collectors, timeout=self.interrupt_timeout)
        if not pending:
            return

        proc.terminate()

        _, pending = await asyncio.wait(pending, timeout=self.terminate_timeout)
        if not pending:
            return

        proc.kill()

        await asyncio.wait(pending)

    async def _main_task(self, proc: Process, wait_task: asyncio.Task[int]) -> bool:
        """
        Control interruption flow.
        Return ``True`` if the process had a non-zero exit code during shutdown.
        """
        try:
            await proc.wait()
        except asyncio.CancelledError:
            # SIGINT causes the task to be cancelled. We first need to uncancel it
            # (if possible) since we don't plan to just give up.
            if self.main_task and hasattr(self.main_task, "uncancel"):
                # Task.uncancel has been added in Python 3.11
                self.main_task.uncancel()

            # Gracefully shutdown procss.
            await self._shutdown_process(proc)

            # Return whether at this point, the process' return code is != 0
            # so we can raise KeyboardInterrupt.
            return wait_task.result() != 0
        else:
            return False

    async def _read_stream(
        self,
        stream: asyncio.StreamReader,
        out_stream: BinaryIO,
        out_buffer: list[bytes],
    ) -> None:
        """
        Read a stream chunk by chunk, append it to ``out_buffer``, and write it to ``out_stream``.
        """
        chunk_parts: list[bytes] = []
        line_sep = b"\n"
        is_eof = False
        while not is_eof:
            # Note that stream.readline() has a size limit of _ASYNCIO_LINE_LENGTH_LIMIT,
            # but doesn't allow to handle cases where this limit is exceeded
            # (https://docs.python.org/3/library/asyncio-stream.html#asyncio.StreamReader.readline).
            # Instead, we use stream.readuntil(line_sep) to read until a line break
            # (https://docs.python.org/3/library/asyncio-stream.html#asyncio.StreamReader.readuntil),
            # which provides error handling through the IncompleteReadError and LimitOverrunError
            # exceptions.
            try:
                chunk_parts.append(await stream.readuntil(line_sep))
                # If we reach this point, the last string in chunk_parts ends with line_sep.
            except asyncio.exceptions.IncompleteReadError as exc:
                # EOF was reached before finding line_sep. exc.partial is what was read so far,
                # and since our separator is one byte long, it won't include the separator,
                # and there will be no more data in the stream afterwards.
                chunk_parts.append(exc.partial)
                is_eof = True
            except asyncio.exceptions.LimitOverrunError as exc:
                # There's more data than _ASYNCIO_LINE_LENGTH_LIMIT, and it's still available
                # for reads. The exception tells us how much data is available though.
                chunk_part = await stream.read(exc.consumed)
                chunk_parts.append(chunk_part)
                # There should be always exc.consumed bytes directly available (without waiting),
                # and exc.consumed should always be > 0. So stream.read() should never return an
                # empty buffer in this case; if it still does, we ignore our knowledge that there
                # should be data and assume that the chunk is complete and EOF has been reached.
                if chunk_part:
                    continue
                is_eof = True

            # Re-combine the line (including separator, if EOF wasn't found).
            chunk = b"".join(chunk_parts)
            chunk_parts.clear()
            if not chunk:
                # This should only happen if is_eof is True.
                break

            out_buffer.append(chunk)
            out_stream.write(chunk)
            out_stream.flush()

    async def _stream_subprocess(
        self,
        args: Sequence[str] | str,
        *,
        env: Mapping[str, str] | None,
    ) -> tuple[bool, int]:
        """
        Start the process, all tasks, and wait for them to finish.
        Return a tuple ``(is_canceled, return_code)``.
        """
        if isinstance(args, str):
            proc = await asyncio.create_subprocess_shell(
                args,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=_ASYNCIO_LINE_LENGTH_LIMIT,  # increase line length limit from the default 64 KiB
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                *args,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=_ASYNCIO_LINE_LENGTH_LIMIT,  # increase line length limit from the default 64 KiB
            )

        # These assumptions are true since we pass PIPE to stdout/stderr,
        # but mypy doesn't know that.
        assert proc.stdout is not None
        assert proc.stderr is not None

        # Note that we write everything to sys.stdout, similar to how popen()
        # operates by default.
        self.collectors.append(
            self.loop.create_task(
                self._read_stream(proc.stdout, sys.stdout.buffer, self.stdout)
            )
        )
        self.collectors.append(
            self.loop.create_task(
                self._read_stream(proc.stderr, sys.stdout.buffer, self.stderr)
            )
        )

        # The wait task gives us the return code.
        wait_task: asyncio.Task[int] = self.loop.create_task(proc.wait())
        self.collectors.append(wait_task)

        # The main task controls the flow (when interrupting).
        self.main_task = self.loop.create_task(self._main_task(proc, wait_task))

        # We wait for all tasks to finish and extract the return code.
        await asyncio.wait([*self.collectors, self.main_task])
        return self.main_task.result(), wait_task.result()

    def run(
        self,
        args: Sequence[str] | str,
        *,
        env: Mapping[str, str] | None = None,
    ) -> tuple[int, bytes, bytes]:
        """
        Run the command with the given environment.
        Return the process' return code, standard output, and standard error.

        Note that this function is **NOT** thread-safe, since we have to
        add a SIGINT handler to the event loop and later remove it.
        """
        is_terminating = [False]

        def handle_sigint() -> None:
            # Don't handle it twice.
            if is_terminating[0]:
                return
            is_terminating[0] = True

            # Cancel the main task. This triggers graceful shutdown.
            if self.main_task:
                self.main_task.cancel()

        self.loop.add_signal_handler(signal.SIGINT, handle_sigint)
        try:
            is_canceled, return_code = self.loop.run_until_complete(
                self._stream_subprocess(args, env=env)
            )
        finally:
            self.loop.remove_signal_handler(signal.SIGINT)
        sys.stdout.flush()
        if is_canceled:
            raise KeyboardInterrupt
        return return_code, b"".join(self.stdout), b"".join(self.stderr)


def tee_popen(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    interrupt_timeout: float | None = DEFAULT_INTERRUPT_TIMEOUT,
    terminate_timeout: float | None = DEFAULT_TERMINATE_TIMEOUT,
) -> tuple[int, str, str]:
    """
    Run the command with the given environment.
    Return a tuple ``(return_code, stdout, stderr)``.
    Standard output and standard error are also printed to ``sys.stdout``.
    """
    popen_args: Sequence[str] | str = args
    if sys.platform.startswith("win") and args[0].casefold().endswith((".bat", ".cmd")):
        popen_args = _windows_batch_command(args, env)

    loop = asyncio.get_event_loop()
    teesub = _TeeSubprocess(
        loop=loop,
        interrupt_timeout=interrupt_timeout,
        terminate_timeout=terminate_timeout,
    )
    return_code, out, err = teesub.run(popen_args, env=env)
    ret_out = decode_output(out)
    ret_err = decode_output(err)
    return return_code, ret_out, ret_err
