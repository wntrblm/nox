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
import sys
from typing import Any, Iterable, List, Optional, Sequence, Union

import py

from nox.logger import logger
from nox.popen import popen


class CommandFailed(Exception):
    """Raised when an executed command returns a non-success status code."""

    def __init__(self, reason: str = None) -> None:
        super(CommandFailed, self).__init__(reason)
        self.reason = reason


def which(program: str, paths: Optional[List[str]]) -> str:
    """Finds the full path to an executable."""
    full_path = None

    if paths:
        full_path = py.path.local.sysfind(program, paths=paths)

    if full_path:
        return full_path.strpath

    full_path = py.path.local.sysfind(program)

    if full_path:
        return full_path.strpath

    logger.error("Program {} not found.".format(program))
    raise CommandFailed("Program {} not found".format(program))


def _clean_env(env: Optional[dict]) -> Optional[dict]:
    if env is None:
        return None

    clean_env = {}

    # Ensure systemroot is passed down, otherwise Windows will explode.
    clean_env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")

    clean_env.update(env)
    return clean_env


def run(
    args: Sequence[str],
    *,
    env: Optional[dict] = None,
    silent: bool = False,
    paths: Optional[List[str]] = None,
    success_codes: Optional[Iterable[int]] = None,
    log: bool = True,
    external: bool = False,
    **popen_kws: Any
) -> Union[str, bool]:
    """Run a command-line program."""

    if success_codes is None:
        success_codes = [0]

    cmd, args = args[0], args[1:]
    full_cmd = "{} {}".format(cmd, " ".join(args))

    cmd_path = which(cmd, paths)

    if log:
        logger.info(full_cmd)

        is_external_tool = paths is not None and not any(
            cmd_path.startswith(path) for path in paths
        )
        if is_external_tool:
            if external == "error":
                logger.error(
                    "Error: {} is not installed into the virtualenv, it is located at {}. "
                    "Pass external=True into run() to explicitly allow this.".format(
                        cmd, cmd_path
                    )
                )
                raise CommandFailed("External program disallowed.")
            elif external is False:
                logger.warning(
                    "Warning: {} is not installed into the virtualenv, it is located at {}. This might cause issues! "
                    "Pass external=True into run() to silence this message.".format(
                        cmd, cmd_path
                    )
                )

    env = _clean_env(env)

    try:
        return_code, output = popen(
            [cmd_path] + list(args), silent=silent, env=env, **popen_kws
        )

        if return_code not in success_codes:
            logger.error(
                "Command {} failed with exit code {}{}".format(
                    full_cmd, return_code, ":" if silent else ""
                )
            )

            if silent:
                sys.stderr.write(output)

            raise CommandFailed("Returned code {}".format(return_code))

        if output:
            logger.output(output)

        return output if silent else True

    except KeyboardInterrupt:
        logger.error("Interrupted...")
        raise
