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

import contextlib
import locale
import subprocess
import sys
from typing import IO, Mapping, Optional, Sequence, Tuple, Union


def shutdown_process(proc: subprocess.Popen) -> Tuple[bytes, bytes]:
    """Gracefully shutdown a child process."""

    with contextlib.suppress(subprocess.TimeoutExpired):
        return proc.communicate(timeout=0.3)

    proc.terminate()

    with contextlib.suppress(subprocess.TimeoutExpired):
        return proc.communicate(timeout=0.2)

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
        if second_encoding.casefold() in ("utf8", "utf-8"):
            raise

        return output.decode(second_encoding)


def popen(
    args: Sequence[str],
    env: Optional[Mapping[str, str]] = None,
    silent: bool = False,
    stdout: Optional[Union[int, IO]] = None,
    stderr: Union[int, IO] = subprocess.STDOUT,
) -> Tuple[int, str]:
    if silent and stdout is not None:
        raise ValueError(
            "Can not specify silent and stdout; passing a custom stdout always silences the commands output in Nox's log."
        )

    if silent:
        stdout = subprocess.PIPE

    proc = subprocess.Popen(args, env=env, stdout=stdout, stderr=stderr)

    try:
        out, err = proc.communicate()
        sys.stdout.flush()

    except KeyboardInterrupt:
        out, err = shutdown_process(proc)
        if proc.returncode != 0:
            raise

    return_code = proc.wait()

    return return_code, decode_output(out) if out else ""
