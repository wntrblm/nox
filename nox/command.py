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
import shlex
import shutil
import sys
from typing import Any, Iterable, Sequence

from nox.logger import logger
from nox.popen import popen

if sys.version_info < (3, 8):  # pragma: no cover
    from typing_extensions import Literal
else:  # pragma: no cover
    from typing import Literal


class CommandFailed(Exception):
    """Raised when an executed command returns a non-success status code."""

    def __init__(self, reason: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason


def which(program: str, paths: list[str] | None) -> str:
    """Finds the full path to an executable."""
    if paths is not None:
        full_path = shutil.which(program, path=os.pathsep.join(paths))
        if full_path:
            return full_path

    full_path = shutil.which(program)
    if full_path:
        return full_path

    logger.error(f"Program {program} not found.")
    raise CommandFailed(f"Program {program} not found")


def _clean_env(env: dict[str, str] | None) -> dict[str, str] | None:
    if env is None:
        return None

    clean_env = {}

    # Ensure systemroot is passed down, otherwise Windows will explode.
    clean_env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")

    clean_env.update(env)
    return clean_env


def _shlex_join(args: Sequence[str]) -> str:
    return " ".join(shlex.quote(os.fspath(arg)) for arg in args)


def run(
    args: Sequence[str],
    *,
    env: dict[str, str] | None = None,
    silent: bool = False,
    paths: list[str] | None = None,
    success_codes: Iterable[int] | None = None,
    log: bool = True,
    external: Literal["error"] | bool = False,
    **popen_kws: Any,
) -> str | bool:
    """Run a command-line program."""

    if success_codes is None:
        success_codes = [0]

    cmd, args = args[0], args[1:]
    full_cmd = f"{cmd} {_shlex_join(args)}"

    cmd_path = which(cmd, paths)

    if log:
        logger.info(full_cmd)

        is_external_tool = paths is not None and not any(
            cmd_path.startswith(path) for path in paths
        )
        if is_external_tool:
            if external == "error":
                logger.error(
                    f"Error: {cmd} is not installed into the virtualenv, it is located"
                    f" at {cmd_path}. Pass external=True into run() to explicitly allow"
                    " this."
                )
                raise CommandFailed("External program disallowed.")
            elif external is False:
                logger.warning(
                    f"Warning: {cmd} is not installed into the virtualenv, it is"
                    f" located at {cmd_path}. This might cause issues! Pass"
                    " external=True into run() to silence this message."
                )

    env = _clean_env(env)

    try:
        return_code, output = popen(
            [cmd_path] + list(args), silent=silent, env=env, **popen_kws
        )

        if return_code not in success_codes:
            suffix = ":" if silent else ""
            logger.error(
                f"Command {full_cmd} failed with exit code {return_code}{suffix}"
            )

            if silent:
                sys.stderr.write(output)

            raise CommandFailed(f"Returned code {return_code}")

        if output:
            logger.output(output)

        return output if silent else True

    except KeyboardInterrupt:
        logger.error("Interrupted...")
        raise
