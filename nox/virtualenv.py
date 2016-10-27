# Copyright 2016 Jon Wayne Parrott
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
import shutil

from nox.command import Command
from nox.logger import logger


class ProcessEnv(object):
    """A environment with a 'bin' directory and a set of 'env' vars."""

    def __init__(self, bin=None, env=None):
        self._bin = bin
        self.env = os.environ.copy()

        if env is not None:
            self.env.update(env)

        if self.bin:
            self.env['PATH'] = ':'.join([self.bin, self.env.get('PATH')])

    @property
    def bin(self):
        return self._bin

    def run(self, args, in_venv=True):
        """Runs a command. By default, the command runs within the
        environment."""
        return Command(
            args=args,
            env=self.env if in_venv else None,
            silent=True,
            path=self.bin if in_venv else None).run()


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
    def bin(self):
        """Returns the location of the virtualenv's bin folder."""
        if platform.system() == 'Windows':
            return os.path.join(self.location, 'Scripts')
        else:
            return os.path.join(self.location, 'bin')

    def create(self):
        """Create the virtualenv."""
        if not self._clean_location():
            logger.debug('Re-using existing virtualenv.')
            return False

        cmd = ['virtualenv', self.location]

        if self.interpreter:
            cmd.extend(['-p', self.interpreter])

        self.run(cmd, in_venv=False)

        return True

    def install(self, *args):
        self.run(('pip', 'install', '--upgrade') + args)
