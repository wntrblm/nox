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

__lazy_modules__ = {"nox.logger", "shlex", "shutil"}

import os
import shlex
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Literal, overload

from nox.logger import logger
from nox.popen import (
    DEFAULT_INTERRUPT_TIMEOUT,
    DEFAULT_TERMINATE_TIMEOUT,
    popen,
    popen_background,
    shutdown_process,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from typing import IO

__all__ = [
    "BackgroundCommand",
    "CommandFailed",
    "ExternalType",
    "run",
    "run_background",
    "which",
]

_PLATFORM = sys.platform


def __dir__() -> list[str]:
    return __all__


ExternalType = Literal["error", True, False]


class CommandFailed(Exception):
    """Raised when an executed command returns a non-success status code."""

    def __init__(
        self, reason: str | None = None, *, return_code: int | None = None
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.return_code = return_code


def which(
    program: str | os.PathLike[str], paths: Sequence[str | os.PathLike[str]] | None
) -> str:
    """Finds the full path to an executable."""
    if paths is not None:
        full_path = shutil.which(program, path=os.pathsep.join(str(p) for p in paths))
        if full_path:
            return os.fspath(full_path)

    full_path = shutil.which(program)
    if full_path:
        return os.fspath(full_path)

    logger.error(f"Program {program} not found.")
    msg = f"Program {program} not found"
    raise CommandFailed(msg)


def _clean_env(env: Mapping[str, str | None] | None = None) -> dict[str, str] | None:
    if env is None:
        return None

    clean_env = {k: v for k, v in env.items() if v is not None}

    # Ensure systemroot is passed down, otherwise Windows will explode.
    if _PLATFORM.startswith("win"):
        clean_env.setdefault("SYSTEMROOT", os.environ.get("SYSTEMROOT", ""))

    return clean_env


def _shlex_join(args: Sequence[str | os.PathLike[str]]) -> str:
    return " ".join(shlex.quote(os.fspath(arg)) for arg in args)


def _prepare_run(
    args: Sequence[str | os.PathLike[str]],
    *,
    paths: Sequence[str | os.PathLike[str]] | None,
    log: bool,
    external: ExternalType,
) -> tuple[list[str], str]:
    """Resolve the executable, log the command, and enforce the external policy."""
    cmd, args = args[0], args[1:]
    full_cmd = f"{cmd} {_shlex_join(args)}"

    cmd_path = which(os.fspath(cmd), paths)
    str_args = [os.fspath(arg) for arg in args]

    if log:
        logger.info(full_cmd)

    is_external_tool = paths is not None and not any(
        cmd_path.startswith(str(path)) for path in paths
    )
    if is_external_tool:
        if external == "error":
            logger.error(
                f"Error: {cmd} is not installed into the virtualenv, it is located"
                f" at {cmd_path}. Pass external=True into run() to explicitly allow"
                " this."
            )
            msg = "External program disallowed."
            raise CommandFailed(msg)
        if external is False and log:
            logger.warning(
                f"Warning: {cmd} is not installed into the virtualenv, it is"
                f" located at {cmd_path}. This might cause issues! Pass"
                " external=True into run() to silence this message."
            )

    return [cmd_path, *str_args], full_cmd


@overload
def run(
    args: Sequence[str | os.PathLike[str]],
    *,
    env: Mapping[str, str | None] | None = ...,
    silent: Literal[True],
    paths: Sequence[str | os.PathLike[str]] | None = ...,
    success_codes: Iterable[int] | None = ...,
    log: bool = ...,
    external: ExternalType = ...,
    stdout: int | IO[str] | None = ...,
    stderr: int | IO[str] | None = ...,
    interrupt_timeout: float | None = ...,
    terminate_timeout: float | None = ...,
) -> str: ...


@overload
def run(
    args: Sequence[str | os.PathLike[str]],
    *,
    env: Mapping[str, str | None] | None = ...,
    silent: Literal[False] = ...,
    paths: Sequence[str | os.PathLike[str]] | None = ...,
    success_codes: Iterable[int] | None = ...,
    log: bool = ...,
    external: ExternalType = ...,
    stdout: int | IO[str] | None = ...,
    stderr: int | IO[str] | None = ...,
    interrupt_timeout: float | None = ...,
    terminate_timeout: float | None = ...,
) -> bool: ...


@overload
def run(
    args: Sequence[str | os.PathLike[str]],
    *,
    env: Mapping[str, str | None] | None = ...,
    silent: bool,
    paths: Sequence[str | os.PathLike[str]] | None = ...,
    success_codes: Iterable[int] | None = ...,
    log: bool = ...,
    external: ExternalType = ...,
    stdout: int | IO[str] | None = ...,
    stderr: int | IO[str] | None = ...,
    interrupt_timeout: float | None = ...,
    terminate_timeout: float | None = ...,
) -> str | bool: ...


def run(
    args: Sequence[str | os.PathLike[str]],
    *,
    env: Mapping[str, str | None] | None = None,
    silent: bool = False,
    paths: Sequence[str | os.PathLike[str]] | None = None,
    success_codes: Iterable[int] | None = None,
    log: bool = True,
    external: ExternalType = False,
    stdout: int | IO[str] | None = None,
    stderr: int | IO[str] | None = subprocess.STDOUT,
    interrupt_timeout: float | None = DEFAULT_INTERRUPT_TIMEOUT,
    terminate_timeout: float | None = DEFAULT_TERMINATE_TIMEOUT,
) -> str | bool:
    """Run a command-line program."""

    if success_codes is None:
        success_codes = [0]

    popen_args, full_cmd = _prepare_run(args, paths=paths, log=log, external=external)

    env = _clean_env(env)

    try:
        return_code, output = popen(
            popen_args,
            silent=silent,
            env=env,
            stdout=stdout,
            stderr=stderr,
            interrupt_timeout=interrupt_timeout,
            terminate_timeout=terminate_timeout,
        )

        if return_code not in success_codes:
            suffix = ":" if (silent and output) else ""
            logger.error(
                f"Command {full_cmd} failed with exit code {return_code}{suffix}"
            )

            if silent and output:
                logger.error(output)

            msg = f"Returned code {return_code}"
            raise CommandFailed(msg, return_code=return_code)

        if output:
            logger.output(output)

    except KeyboardInterrupt:
        logger.error("Interrupted...")
        raise

    return output if silent else True


class BackgroundCommand:
    """A handle to a command started in the background.

    Instances are returned by :meth:`nox.sessions.Session.background`. The
    process keeps running while the rest of the session executes; call
    :meth:`stop` (or use the object as a context manager) to shut it down. Any
    background commands still running when the session ends are stopped
    automatically.
    """

    def __init__(
        self,
        process: subprocess.Popen[bytes],
        *,
        interrupt_timeout: float | None = DEFAULT_INTERRUPT_TIMEOUT,
        terminate_timeout: float | None = DEFAULT_TERMINATE_TIMEOUT,
    ) -> None:
        self.process = process
        self.interrupt_timeout = interrupt_timeout
        self.terminate_timeout = terminate_timeout

    @property
    def returncode(self) -> int | None:
        """The command's exit code, or ``None`` while it is still running."""
        return self.process.returncode

    def poll(self) -> int | None:
        """Check whether the command has finished without blocking."""
        return self.process.poll()

    def wait(self, timeout: float | None = None) -> int:
        """Wait for the command to finish and return its exit code."""
        return self.process.wait(timeout)

    def stop(self) -> int:
        """Gracefully stop the command and return its exit code.

        Nothing happens if the command has already finished. Otherwise it is
        given ``interrupt_timeout`` seconds to exit before being terminated, and
        ``terminate_timeout`` seconds more before being killed.
        """
        if self.process.poll() is None:
            shutdown_process(
                self.process, self.interrupt_timeout, self.terminate_timeout
            )
        return self.process.wait()

    def __enter__(self) -> BackgroundCommand:  # noqa: PYI034
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()


def run_background(
    args: Sequence[str | os.PathLike[str]],
    *,
    env: Mapping[str, str | None] | None = None,
    paths: Sequence[str | os.PathLike[str]] | None = None,
    log: bool = True,
    external: ExternalType = False,
    stdout: int | IO[str] | None = None,
    stderr: int | IO[str] | None = None,
    interrupt_timeout: float | None = DEFAULT_INTERRUPT_TIMEOUT,
    terminate_timeout: float | None = DEFAULT_TERMINATE_TIMEOUT,
) -> BackgroundCommand:
    """Start a command-line program in the background."""
    popen_args, _full_cmd = _prepare_run(args, paths=paths, log=log, external=external)

    process = popen_background(
        popen_args, env=_clean_env(env), stdout=stdout, stderr=stderr
    )

    return BackgroundCommand(
        process,
        interrupt_timeout=interrupt_timeout,
        terminate_timeout=terminate_timeout,
    )
