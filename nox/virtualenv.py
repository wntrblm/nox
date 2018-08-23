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
_BLACKLISTED_ENV_VARS = frozenset([
    'PIP_RESPECT_VIRTUALENV',
    'PIP_REQUIRE_VIRTUALENV',
    '__PYVENV_LAUNCHER__',
])


class ProcessEnv:
    """A environment with a 'bin' directory and a set of 'env' vars."""

    def __init__(self, bin=None, env=None):
        self._bin = bin
        self.env = os.environ.copy()

        if env is not None:
            self.env.update(env)

        for key in _BLACKLISTED_ENV_VARS:
            self.env.pop(key, None)

        if self.bin:
            self.env['PATH'] = ':'.join([self.bin, self.env.get('PATH')])

    @property
    def bin(self):
        return self._bin


def locate_via_py(version):
    """Find the Python executable using the Windows launcher.

    This is based on :pep:397 which details that executing
    ``py.exe -{version}`` should execute python with the requested
    version. We then make the python process print out its full
    executable path which we use as the location for the version-
    specific Python interpreter.

    Args:
        version (str): The desired Python version.

    Returns:
        Optional[str]: The full executable path for the Python ``version``,
        if it is found.
    """
    script = 'import sys; print(sys.executable)'
    py_exe = py.path.local.sysfind('py')
    if py_exe is not None:
        try:
            return py_exe.sysexec('-' + version, '-c', script).strip()
        except py.process.cmdexec.Error:
            return None


class VirtualEnv(ProcessEnv):
    """Virtualenv management class."""

    def __init__(self, location, interpreter=None, reuse_existing=False):
        self.location = os.path.abspath(location)
        self.interpreter = interpreter
        self.reuse_existing = reuse_existing
        super(VirtualEnv, self).__init__()

    def _clean_location(self):
        """Deletes any existing virtualenv"""
        if os.path.exists(self.location):
            if self.reuse_existing:
                return False
            else:
                shutil.rmtree(self.location)

        return True

    @property
    def _resolved_interpreter(self):
        """Return the interpreter, appropriately resolved for the platform.

        Based heavily on tox's implementation (tox/interpreters.py).
        """
        # If there is no assigned interpreter, then use the same one used by
        # Nox.
        if self.interpreter is None:
            return sys.executable

        # If this is just a X.Y or X.Y.Z string, stick `python` in front of it.
        if re.match(r'^\d\.\d\.?\d?$', self.interpreter):
            self.interpreter = 'python{}'.format(self.interpreter)

        # Sanity check: We only need the rest of this behavior on Windows.
        if platform.system() != 'Windows':
            return self.interpreter

        # We may have gotten a fully-qualified intepreter path (for someone
        # _only_ testing on Windows); accept this.
        if py.path.local.sysfind(self.interpreter):
            return self.interpreter

        # If this is a standard Unix "pythonX.Y" name, it should be found
        # in a standard location in Windows, and if not, the py.exe launcher
        # should be able to find it from the information in the registry.
        match = re.match(r'^python(?P<ver>\d\.\d)$', self.interpreter)
        if match:
            version = match.group('ver')
            # Ask the Python launcher to find the interpreter.
            path_from_launcher = locate_via_py(version)
            if path_from_launcher:
                return path_from_launcher

        # If we got this far, then we were unable to resolve the interpreter
        # to an actual executable; raise an exception.
        raise RuntimeError('Unable to locate Python interpreter "{}".'.format(
            self.interpreter,
        ))

    @property
    def bin(self):
        """Returns the location of the virtualenv's bin folder."""
        if platform.system() == 'Windows':
            return os.path.join(self.location, 'Scripts')
        else:
            return os.path.join(self.location, 'bin')

    def create(self):
        """Create the virtualenv."""
        if not self._clean_location():
            logger.debug(
                'Re-using existing virtualenv at {}.'.format(self.location))
            return False

        cmd = [sys.executable, '-m', 'virtualenv', self.location]

        if self.interpreter:
            cmd.extend(['-p', self._resolved_interpreter])

        logger.info(
            'Creating virtualenv using {} in {}'.format(
                os.path.basename(self._resolved_interpreter), self.location))
        nox.command.run(cmd, silent=True, log=False)

        return True
