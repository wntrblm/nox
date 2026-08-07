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

__lazy_modules__ = {"contextlib", "itertools", "locale"}

import contextlib
import itertools
import locale
import os
import subprocess
import sys
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "DEFAULT_INTERRUPT_TIMEOUT",
    "DEFAULT_TERMINATE_TIMEOUT",
    "decode_output",
    "popen",
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


def popen(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    silent: bool = False,
    stdout: int | IO[str] | None = None,
    stderr: int | IO[str] | None = subprocess.STDOUT,
    interrupt_timeout: float | None = DEFAULT_INTERRUPT_TIMEOUT,
    terminate_timeout: float | None = DEFAULT_TERMINATE_TIMEOUT,
) -> tuple[int, str]:
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
        out, _err = proc.communicate()
        sys.stdout.flush()

    except KeyboardInterrupt:
        out, _err = shutdown_process(proc, interrupt_timeout, terminate_timeout)
        if proc.returncode != 0:
            raise

    return_code = proc.wait()

    return return_code, decode_output(out) if out else ""
