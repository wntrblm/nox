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
import platform
import re
import shutil
import sys
from socket import gethostbyname
from typing import Any, List, Mapping, Optional, Tuple, Union

import py

import nox
import nox.command
from nox.logger import logger

from . import _typing

# Problematic environment variables that are stripped from all commands inside
# of a virtualenv. See https://github.com/theacodes/nox/issues/44
_BLACKLISTED_ENV_VARS = frozenset(
    ["PIP_RESPECT_VIRTUALENV", "PIP_REQUIRE_VIRTUALENV", "__PYVENV_LAUNCHER__"]
)
_SYSTEM = platform.system()
_ENABLE_STALENESS_CHECK = "NOX_ENABLE_STALENESS_CHECK" in os.environ


class InterpreterNotFound(OSError):
    def __init__(self, interpreter: str) -> None:
        super().__init__(f"Python interpreter {interpreter} not found")
        self.interpreter = interpreter


class ProcessEnv:
    """A environment with a 'bin' directory and a set of 'env' vars."""

    location: str

    # Does this environment provide any process isolation?
    is_sandboxed = False

    # Special programs that aren't included in the environment.
    allowed_globals = ()  # type: _typing.ClassVar[Tuple[Any, ...]]

    def __init__(
        self, bin_paths: None = None, env: Optional[Mapping[str, str]] = None
    ) -> None:
        self._bin_paths = bin_paths
        self.env = os.environ.copy()
        self._reused = False

        if env is not None:
            self.env.update(env)

        for key in _BLACKLISTED_ENV_VARS:
            self.env.pop(key, None)

        if self.bin_paths:
            self.env["PATH"] = os.pathsep.join(
                self.bin_paths + [self.env.get("PATH", "")]
            )

    @property
    def bin_paths(self) -> Optional[List[str]]:
        return self._bin_paths

    @property
    def bin(self) -> str:
        """The first bin directory for the virtualenv."""
        paths = self.bin_paths
        if paths is None:
            raise ValueError("The environment does not have a bin directory.")
        return paths[0]

    def create(self) -> bool:
        raise NotImplementedError("ProcessEnv.create should be overwritten in subclass")


def locate_via_py(version: str) -> Optional[str]:
    """Find the Python executable using the Windows Launcher.

    This is based on :pep:397 which details that executing
    ``py.exe -{version}`` should execute python with the requested
    version. We then make the python process print out its full
    executable path which we use as the location for the version-
    specific Python interpreter.

    Args:
        version (str): The desired Python version to pass to ``py.exe``. Of the form
            ``X.Y`` or ``X.Y-32``. For example, a usage of the Windows Launcher might
            be ``py -3.6-32``.

    Returns:
        Optional[str]: The full executable path for the Python ``version``,
        if it is found.
    """
    script = "import sys; print(sys.executable)"
    py_exe = py.path.local.sysfind("py")
    if py_exe is not None:
        try:
            return py_exe.sysexec("-" + version, "-c", script).strip()
        except py.process.cmdexec.Error:
            return None
    return None


def locate_using_path_and_version(version: str) -> Optional[str]:
    """Check the PATH's python interpreter and return it if the version
    matches.

    On systems without version-named interpreters and with missing
    launcher (which is on all Windows Anaconda installations),
    we search the PATH for a plain "python" interpreter and accept it
    if its --version matches the specified interpreter version.

    Args:
        version (str): The desired Python version. Of the form ``X.Y``.

    Returns:
        Optional[str]: The full executable path for the Python ``version``,
        if it is found.
    """
    if not version:
        return None

    script = "import platform; print(platform.python_version())"
    path_python = py.path.local.sysfind("python")
    if path_python:
        try:
            prefix = f"{version}."
            version_string = path_python.sysexec("-c", script).strip()
            if version_string.startswith(prefix):
                return str(path_python)
        except py.process.cmdexec.Error:
            return None

    return None


class PassthroughEnv(ProcessEnv):
    """Represents the environment used to run nox itself

    For now, this class is empty but it might contain tools to grasp some
    hints about the actual env.
    """

    @staticmethod
    def is_offline() -> bool:
        """As of now this is only used in conda_install"""
        return CondaEnv.is_offline()  # pragma: no cover


class CondaEnv(ProcessEnv):
    """Conda environment management class.

    Args:
        location (str): The location on the filesystem where the conda environment
            should be created.
        interpreter (Optional[str]): The desired Python version. Of the form

            * ``X.Y``, e.g. ``3.5``
            * ``X.Y-32``. For example, a usage of the Windows Launcher might
              be ``py -3.6-32``
            * ``X.Y.Z``, e.g. ``3.4.9``
            * ``pythonX.Y``, e.g. ``python2.7``
            * A path in the filesystem to a Python executable

            If not specified, this will use the currently running Python.
        reuse_existing (Optional[bool]): Flag indicating if the conda environment
            should be reused if it already exists at ``location``.
    """

    is_sandboxed = True
    allowed_globals = ("conda",)

    def __init__(
        self,
        location: str,
        interpreter: Optional[str] = None,
        reuse_existing: bool = False,
        venv_params: Any = None,
    ):
        self.location_name = location
        self.location = os.path.abspath(location)
        self.interpreter = interpreter
        self.reuse_existing = reuse_existing
        self.venv_params = venv_params if venv_params else []
        super(CondaEnv, self).__init__()

    def _clean_location(self) -> bool:
        """Deletes existing conda environment"""
        if os.path.exists(self.location):
            if self.reuse_existing:
                return False
            else:
                cmd = ["conda", "remove", "--yes", "--prefix", self.location, "--all"]
                nox.command.run(cmd, silent=True, log=False)
                # Make sure that location is clean
                try:
                    shutil.rmtree(self.location)
                except FileNotFoundError:
                    pass

        return True

    @property
    def bin_paths(self) -> List[str]:
        """Returns the location of the conda env's bin folder."""
        # see https://docs.anaconda.com/anaconda/user-guide/tasks/integration/python-path/#examples
        if _SYSTEM == "Windows":
            return [self.location, os.path.join(self.location, "Scripts")]
        else:
            return [os.path.join(self.location, "bin")]

    def create(self) -> bool:
        """Create the conda env."""
        if not self._clean_location():
            logger.debug(f"Re-using existing conda env at {self.location_name}.")

            self._reused = True

            return False

        cmd = ["conda", "create", "--yes", "--prefix", self.location]

        cmd.extend(self.venv_params)

        # Ensure the pip package is installed.
        cmd.append("pip")

        if self.interpreter:
            python_dep = f"python={self.interpreter}"
        else:
            python_dep = "python"
        cmd.append(python_dep)

        logger.info(f"Creating conda env in {self.location_name} with {python_dep}")
        nox.command.run(cmd, silent=True, log=nox.options.verbose or False)

        return True

    @staticmethod
    def is_offline() -> bool:
        """Return `True` if we are sure that the user is not able to connect to https://repo.anaconda.com.

        Since an HTTP proxy might be correctly configured for `conda` using the `.condarc` `proxy_servers` section,
        while not being correctly configured in the OS environment variables used by all other tools including python
        `urllib` or `requests`, we are basically not able to do much more than testing the DNS resolution.

        See details in this explanation: https://stackoverflow.com/a/62486343/7262247
        """
        try:
            # DNS resolution to detect situation (1) or (2).
            host = gethostbyname("repo.anaconda.com")
            return host is None
        except:  # pragma: no cover # noqa E722
            return True


class VirtualEnv(ProcessEnv):
    """Virtualenv management class.

    Args:
        location (str): The location on the filesystem where the virtual environment
            should be created.
        interpreter (Optional[str]): The desired Python version. Of the form

            * ``X.Y``, e.g. ``3.5``
            * ``X.Y-32``. For example, a usage of the Windows Launcher might
              be ``py -3.6-32``
            * ``X.Y.Z``, e.g. ``3.4.9``
            * ``pythonX.Y``, e.g. ``python2.7``
            * A path in the filesystem to a Python executable

            If not specified, this will use the currently running Python.
        reuse_existing (Optional[bool]): Flag indicating if the virtual environment
            should be reused if it already exists at ``location``.
    """

    is_sandboxed = True

    def __init__(
        self,
        location: str,
        interpreter: Optional[str] = None,
        reuse_existing: bool = False,
        *,
        venv: bool = False,
        venv_params: Any = None,
    ):
        self.location_name = location
        self.location = os.path.abspath(location)
        self.interpreter = interpreter
        self._resolved = None  # type: Union[None, str, InterpreterNotFound]
        self.reuse_existing = reuse_existing
        self.venv_or_virtualenv = "venv" if venv else "virtualenv"
        self.venv_params = venv_params if venv_params else []
        super(VirtualEnv, self).__init__(env={"VIRTUAL_ENV": self.location})

    def _clean_location(self) -> bool:
        """Deletes any existing virtual environment"""
        if os.path.exists(self.location):
            if self.reuse_existing and not _ENABLE_STALENESS_CHECK:
                return False
            if (
                self.reuse_existing
                and self._check_reused_environment_type()
                and self._check_reused_environment_interpreter()
            ):
                return False
            else:
                shutil.rmtree(self.location)

        return True

    def _check_reused_environment_type(self) -> bool:
        """Check if reused environment type is the same."""
        path = os.path.join(self.location, "pyvenv.cfg")
        if not os.path.isfile(path):
            # virtualenv < 20.0 does not create pyvenv.cfg
            old_env = "virtualenv"
        else:
            pattern = re.compile("virtualenv[ \t]*=")
            with open(path) as fp:
                old_env = (
                    "virtualenv" if any(pattern.match(line) for line in fp) else "venv"
                )
        return old_env == self.venv_or_virtualenv

    def _check_reused_environment_interpreter(self) -> bool:
        """Check if reused environment interpreter is the same."""
        original = self._read_base_prefix_from_pyvenv_cfg()
        program = (
            "import sys; sys.stdout.write(getattr(sys, 'real_prefix', sys.base_prefix))"
        )

        if original is None:
            output = nox.command.run(
                [self._resolved_interpreter, "-c", program], silent=True, log=False
            )
            assert isinstance(output, str)
            original = output

        created = nox.command.run(
            ["python", "-c", program], silent=True, log=False, paths=self.bin_paths
        )

        return original == created

    def _read_base_prefix_from_pyvenv_cfg(self) -> Optional[str]:
        """Return the base-prefix entry from pyvenv.cfg, if present."""
        path = os.path.join(self.location, "pyvenv.cfg")
        if os.path.isfile(path):
            with open(path) as io:
                for line in io:
                    key, _, value = line.partition("=")
                    if key.strip() == "base-prefix":
                        return value.strip()
        return None

    @property
    def _resolved_interpreter(self) -> str:
        """Return the interpreter, appropriately resolved for the platform.

        Based heavily on tox's implementation (tox/interpreters.py).
        """
        # If there is no assigned interpreter, then use the same one used by
        # Nox.
        if isinstance(self._resolved, Exception):
            raise self._resolved

        if self._resolved is not None:
            return self._resolved

        if self.interpreter is None:
            self._resolved = sys.executable
            return self._resolved

        # Otherwise we need to divine the path to the interpreter. This is
        # designed to accept strings in the form of "2", "2.7", "2.7.13",
        # "2.7.13-32", "python2", "python2.4", etc.
        xy_version = ""
        cleaned_interpreter = self.interpreter

        # If this is just a X, X.Y, or X.Y.Z string, extract just the X / X.Y
        # part and add Python to the front of it.
        match = re.match(r"^(?P<xy_ver>\d(\.\d+)?)(\.\d+)?$", self.interpreter)
        if match:
            xy_version = match.group("xy_ver")
            cleaned_interpreter = f"python{xy_version}"

        # If the cleaned interpreter is on the PATH, go ahead and return it.
        if py.path.local.sysfind(cleaned_interpreter):
            self._resolved = cleaned_interpreter
            return self._resolved

        # The rest of this is only applicable to Windows, so if we don't have
        # an interpreter by now, raise.
        if _SYSTEM != "Windows":
            self._resolved = InterpreterNotFound(self.interpreter)
            raise self._resolved

        # Allow versions of the form ``X.Y-32`` for Windows.
        match = re.match(r"^\d\.\d+-32?$", cleaned_interpreter)
        if match:
            # preserve the "-32" suffix, as the Python launcher expects
            # it.
            xy_version = cleaned_interpreter

        path_from_launcher = locate_via_py(xy_version)
        if path_from_launcher:
            self._resolved = path_from_launcher
            return self._resolved

        path_from_version_param = locate_using_path_and_version(xy_version)
        if path_from_version_param:
            self._resolved = path_from_version_param
            return self._resolved

        # If we got this far, then we were unable to resolve the interpreter
        # to an actual executable; raise an exception.
        self._resolved = InterpreterNotFound(self.interpreter)
        raise self._resolved

    @property
    def bin_paths(self) -> List[str]:
        """Returns the location of the virtualenv's bin folder."""
        if _SYSTEM == "Windows":
            return [os.path.join(self.location, "Scripts")]
        else:
            return [os.path.join(self.location, "bin")]

    def create(self) -> bool:
        """Create the virtualenv or venv."""
        if not self._clean_location():
            logger.debug(
                f"Re-using existing virtual environment at {self.location_name}."
            )

            self._reused = True

            return False

        if self.venv_or_virtualenv == "virtualenv":
            cmd = [sys.executable, "-m", "virtualenv", self.location]
            if self.interpreter:
                cmd.extend(["-p", self._resolved_interpreter])
        else:
            cmd = [self._resolved_interpreter, "-m", "venv", self.location]
        cmd.extend(self.venv_params)

        resolved_interpreter_name = os.path.basename(self._resolved_interpreter)

        logger.info(
            f"Creating virtual environment ({self.venv_or_virtualenv}) using {resolved_interpreter_name} in {self.location_name}"
        )
        nox.command.run(cmd, silent=True, log=nox.options.verbose or False)

        return True
