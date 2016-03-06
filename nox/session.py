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

from nox.command import Command, CommandFailed, FunctionCommand
from nox.logger import logger
from nox.virtualenv import VirtualEnv
import py


class SessionConfig(object):
    """SessionConfig is passed into the session function defined in the
    user's *nox.py*. The session function uses this object to configure the
    virtualenv and tell nox which commands to run within the session.
    """
    def __init__(self, posargs=None):
        self._dependencies = []
        self._commands = []
        self.env = {}
        self._dir = '.'
        self.interpreter = None
        """``None`` or a string indicating the name of the Python interpreter
        to use in the session's virtualenv. If None, the default system
        interpreter is used."""
        self.posargs = posargs or []
        """``None`` or a list of strings. This is set to any extra arguments
        passed to ``nox`` on the commandline."""
        self.reuse_existing_virtualenv = False
        """A boolean indicating whether to recreate or reuse the session's
        virtualenv. If True, then any existing virtualenv will be used. This
        can also be specified globally using the
        ``--reuse-existing-virtualenvs`` argument when running ``nox``."""

    def chdir(self, dir):
        """Set the working directory for any commands that run in this
        session."""
        self._dir = dir

    def run(self, *args, **kwargs):
        """
        Run a command in the session. Commands must be specified as a list of
        strings, for example::

            session.run('py.test', '-k', 'fast', 'tests/')
            session.run('flake8', '--import-order-style=google')

        You **can not** just pass everything as one string. For example, this
        **will not work**::

            session.run('py.test -k fast tests/')

        You can set environment variables for the command using ``env``::

            session.run(
                'bash', '-c', 'echo $SOME_ENV',
                env={'SOME_ENV': 'Hello'})

        You can also tell nox to treat non-zero exit codes as success using
        ``success_codes``. For example, if you wanted to treat the ``py.test``
        "tests discovered, but none selected" error as success::

            session.run(
                'py.test', '-k', 'not slow',
                success_codes=[0, 5])

        :param env: A dictionary of environment variables to expose to the
            command. By default, all evironment variables are passed.
        :type env: dict or None
        :param bool silent: Silence command output, unless the command fails.
            ``False`` by default.
        :param success_codes: A list of return codes that are considered
            successful. By default, only ``0`` is considered success.
        :type success_codes: list, tuple, or None
        """
        if not args:
            raise ValueError('At least one argument required to run().')
        if callable(args[0]):
            if len(args) > 1:
                raise ValueError(
                    'Only one function can be specified at a time to run()')
            self._commands.append(FunctionCommand(args[0]))
        else:
            self._commands.append(Command(args=args, **kwargs))

    def install(self, *args):
        """Install invokes `pip`_ to install packages inside of the session's
        virtualenv.

        To install packages directly::

            session.install('py.test')
            session.install('requests', 'mock')
            session.install('requests[security]==2.9.1')

        To install packages from a `requirements.txt` file::

            session.install('-r', 'requirements.txt')
            session.install('-r', 'requirements-dev.txt')

        To install the current package::

            session.install('.')
            # Install in editable mode.
            session.install('-e', '.')

        .. _pip: https://pip.readthedocs.org
        """
        if not args:
            raise ValueError('At least one argument required to install().')
        self._dependencies.append(args)


class Session(object):
    def __init__(self, name, signature, func, global_config):
        self.name = name
        self.signature = signature
        self.func = func
        self.global_config = global_config

    def _create_config(self):
        self.config = SessionConfig(posargs=self.global_config.posargs)
        self.func(self.config)

    def _create_venv(self):
        self.venv = VirtualEnv(
            os.path.join(self.global_config.envdir, self.name),
            interpreter=self.config.interpreter,
            reuse_existing=(
                self.config.reuse_existing_virtualenv or
                self.global_config.reuse_existing_virtualenvs))
        self.venv.create()

    def _install_dependencies(self):
        for dep in self.config._dependencies:
            self.venv.install(*dep)

    def _run_commands(self):
        env = self.venv.env.copy()
        env.update(self.config.env)

        for command in self.config._commands:
            if isinstance(command, Command):
                command.path = self.venv.bin
                command.env = env
                command()
            else:
                command()

    def execute(self):
        logger.warning('Running session {}'.format(
            self.signature or self.name))

        try:
            self._create_config()
            self._create_venv()
            self._install_dependencies()

            if self.config._dir != '.':
                logger.info(
                    'Changing directory to {}'.format(self.config._dir))

            cwd = py.path.local(self.config._dir).as_cwd()
            with cwd:
                self._run_commands()

            logger.success('Session {} successful. :)'.format(self.name))
            return True

        except CommandFailed as e:
            logger.error('Session {} failed. :('.format(self.name))
            return False

        except KeyboardInterrupt as e:
            logger.error('Session {} interrupted.'.format(self.name))
            raise
