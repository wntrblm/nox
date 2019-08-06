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

import py

import nox.command
from nox.logger import logger

# Problematic environment variables that are stripped from all commands inside
# of a virtualenv. See https://github.com/theacodes/nox/issues/44
_BLACKLISTED_ENV_VARS = frozenset(
    ["PIP_RESPECT_VIRTUALENV", "PIP_REQUIRE_VIRTUALENV", "__PYVENV_LAUNCHER__"]
)
_SYSTEM = platform.system()


class InterpreterNotFound(OSError):
    def __init__(self, interpreter):
        super().__init__("Python interpreter {} not found".format(interpreter))
        self.interpreter = interpreter


class ProcessEnv:
    """A environment with a 'bin' directory and a set of 'env' vars."""

    # Does this environment provide any process isolation?
    is_sandboxed = False

    # Special programs that aren't included in the environment.
    allowed_globals = ()

    def __init__(self, bin=None, env=None):
        self._bin = bin
        self.env = os.environ.copy()

        if env is not None:
            self.env.update(env)

        for key in _BLACKLISTED_ENV_VARS:
            self.env.pop(key, None)

        if self.bin:
            self.env["PATH"] = os.pathsep.join([self.bin, self.env.get("PATH", "")])

    @property
    def bin(self):
        return self._bin


def locate_via_py(version):
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


def _clean_location(self):
    """Deletes any existing path-based environment"""
    if os.path.exists(self.location):
        if self.reuse_existing:
            return False
        else:
            shutil.rmtree(self.location)

    return True


class CondaEnv(ProcessEnv):
    """Conda environemnt management class.

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

    def __init__(self, location, interpreter=None, reuse_existing=False):
        self.location_name = location
        self.location = os.path.abspath(location)
        self.interpreter = interpreter
        self.reuse_existing = reuse_existing
        super(CondaEnv, self).__init__()

    _clean_location = _clean_location

    @property
    def bin(self):
        """Returns the location of the conda env's bin folder."""
        if _SYSTEM == "Windows":
            return os.path.join(self.location, "Scripts")
        else:
            return os.path.join(self.location, "bin")

    def create(self):
        """Create the conda env."""
        if not self._clean_location():
            logger.debug(
                "Re-using existing conda env at {}.".format(self.location_name)
            )
            return False

        cmd = [
            "conda",
            "create",
            "--yes",
            "--prefix",
            self.location,
            # Ensure the pip package is installed.
            "pip",
        ]

        if self.interpreter:
            python_dep = "python={}".format(self.interpreter)
        else:
            python_dep = "python"
        cmd.append(python_dep)

        logger.info(
            "Creating conda env in {} with {}".format(self.location_name, python_dep)
        )
        nox.command.run(cmd, silent=True, log=False)

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

    def __init__(self, location, interpreter=None, reuse_existing=False, *, venv=False):
        self.location_name = location
        self.location = os.path.abspath(location)
        self.interpreter = interpreter
        self._resolved = None
        self.reuse_existing = reuse_existing
        self.venv_or_virtualenv = "venv" if venv else "virtualenv"
        super(VirtualEnv, self).__init__()

    _clean_location = _clean_location

    @property
    def _resolved_interpreter(self):
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
        match = re.match(r"^(?P<xy_ver>\d(\.\d)?)(\.\d+)?$", self.interpreter)
        if match:
            xy_version = match.group("xy_ver")
            cleaned_interpreter = "python{}".format(xy_version)

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
        match = re.match(r"^\d\.\d-32?$", cleaned_interpreter)
        if match:
            # preserve the "-32" suffix, as the Python launcher expects
            # it.
            xy_version = cleaned_interpreter

        path_from_launcher = locate_via_py(xy_version)

        if path_from_launcher:
            self._resolved = path_from_launcher
            return self._resolved

        # If we got this far, then we were unable to resolve the interpreter
        # to an actual executable; raise an exception.
        self._resolved = InterpreterNotFound(self.interpreter)
        raise self._resolved

    @property
    def bin(self):
        """Returns the location of the virtualenv's bin folder."""
        if _SYSTEM == "Windows":
            return os.path.join(self.location, "Scripts")
        else:
            return os.path.join(self.location, "bin")

    def create(self):
        """Create the virtualenv or venv."""
        if not self._clean_location():
            logger.debug(
                "Re-using existing virtual environment at {}.".format(
                    self.location_name
                )
            )
            return False

        cmd = [sys.executable, "-m", self.venv_or_virtualenv, self.location]

        if self.interpreter and self.venv_or_virtualenv == "virtualenv":
            cmd.extend(["-p", self._resolved_interpreter])

        logger.info(
            "Creating virtual environment ({}) using {} in {}".format(
                self.venv_or_virtualenv,
                os.path.basename(self._resolved_interpreter),
                self.location_name,
            )
        )
        nox.command.run(cmd, silent=True, log=False)

        return True
