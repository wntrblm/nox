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

import hashlib
import os
import re
import unicodedata

import py
import six

from nox.command import (
    ChdirCommand, Command, CommandFailed, FunctionCommand, InstallCommand)
from nox.logger import logger
from nox.virtualenv import ProcessEnv, VirtualEnv


def _normalize_path(envdir, path):
    """Normalizes a string to be a "safe" filesystem path for a virtualenv."""
    if isinstance(path, six.binary_type):
        path = path.decode('utf-8')

    path = unicodedata.normalize('NFKD', path).encode('ascii', 'ignore')
    path = path.decode('ascii')
    path = re.sub('[^\w\s-]', '-', path).strip().lower()
    path = re.sub('[-\s]+', '-', path)
    path = path.strip('-')

    full_path = os.path.join(envdir, path)
    if len(full_path) > 100 - len('bin/pythonX.Y'):
        if len(envdir) < 100 - 9:
            path = hashlib.sha1(path.encode('ascii')).hexdigest()[:8]
            full_path = os.path.join(envdir, path)
            logger.warning(
                'The virtualenv name was hashed to avoid being too long.')
        else:
            logger.error(
                'The virtualenv path {} is too long and will cause issues on '
                'some environments. Use the --envdir path to modify where '
                'nox stores virtualenvs.'.format(full_path))

    return full_path


class _SessionQuit(Exception):
    pass


class _SessionSkip(Exception):
    pass


class SessionStatus(object):
    FAIL = False
    SUCCESS = True
    SKIP = 2


class SessionConfig(object):
    """SessionConfig is passed into the session function defined in the
    user's *nox.py*. The session function uses this object to configure the
    virtualenv and tell nox which commands to run within the session.
    """
    def __init__(self, posargs=None):
        self._commands = []
        self.env = {}
        """A dictionary of environment variables to pass into all commands."""
        self.virtualenv = True
        """A boolean indicating whether or not to create a virtualenv. Defaults
        to True."""
        self.virtualenv_dirname = None
        """An optional string that determines the name of the directory
        where the virtualenv will be created. This is relative to the
        --envdir option passed into the nox command. By default, nox will
        generate the name based on the function signature."""
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

    def chdir(self, dir, debug=False):
        """Set the working directory for any commands that run in this
        session after this point."""
        self._commands.append(ChdirCommand(dir, debug=debug))

    cd = chdir

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
            self._commands.append(
                FunctionCommand(args[0], args[1:], kwargs))
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
        if not self.virtualenv:
            raise ValueError(
                'A session without a virtualenv can not install dependencies.')
        if not args:
            raise ValueError('At least one argument required to install().')
        self._commands.append(InstallCommand(args))

    def log(self, *args, **kwargs):
        """Outputs a log during the session."""
        logger.info(*args, **kwargs)

    def error(self, *args, **kwargs):
        """Immediately aborts the session and optionally logs an error."""
        if args or kwargs:
            logger.error(*args, **kwargs)
        raise _SessionQuit()

    def skip(self, *args, **kwargs):
        """Immediately skips the session and optionally logs a warning."""
        if args or kwargs:
            logger.warning(*args, **kwargs)
        raise _SessionSkip()


class Session(object):
    def __init__(self, name, signature, func, global_config):
        self.name = name
        self.signature = signature
        self.func = func
        self.global_config = global_config
        self._should_install_deps = True

    def _create_config(self):
        self.config = SessionConfig(posargs=self.global_config.posargs)

        # By default, nox should quietly change to the directory where
        # the nox.py file is located.
        cwd = os.path.realpath(os.path.dirname(self.global_config.noxfile))
        self.config.chdir(cwd, debug=True)

        # Run the actual session function, passing it the newly-created
        # SessionConfig object.
        try:
            self.func(self.config)
            return SessionStatus.SUCCESS
        except _SessionQuit:
            return SessionStatus.FAIL
        except _SessionSkip:
            return SessionStatus.SKIP

    def _create_venv(self):
        if not self.config.virtualenv:
            self.venv = ProcessEnv()
            self._should_install_deps = False
            return

        virtualenv_name = (
            self.config.virtualenv_dirname or self.signature or self.name)
        self.venv = VirtualEnv(
            _normalize_path(
                self.global_config.envdir, virtualenv_name),
            interpreter=self.config.interpreter,
            reuse_existing=(
                self.config.reuse_existing_virtualenv or
                self.global_config.reuse_existing_virtualenvs))
        self._should_install_deps = self.venv.create()

    def _run_commands(self):
        env = self.venv.env.copy()
        env.update(self.config.env)

        for command in self.config._commands:
            if isinstance(command, Command):
                command(
                    path_override=self.venv.bin, env_fallback=env)
            elif isinstance(command, InstallCommand):
                if not self._should_install_deps:
                    logger.debug(
                        'Skipping installation of "{}".'.format(command))
                    continue
                else:
                    command(self.venv)
            else:
                command()

    def execute(self):
        session_friendly_name = self.signature or self.name
        logger.warning('Running session {}'.format(session_friendly_name))

        try:
            status = self._create_config()

            if status == SessionStatus.FAIL:
                logger.error('Session {} aborted.'.format(
                    session_friendly_name))
                return status
            elif status == SessionStatus.SKIP:
                logger.warning('Session {} skipped.'.format(
                    session_friendly_name))
                return status

            self._create_venv()

            cwd = py.path.local(os.getcwd()).as_cwd()
            with cwd:
                self._run_commands()

            logger.success('Session {} successful. :)'.format(
                session_friendly_name))
            return SessionStatus.SUCCESS

        except CommandFailed:
            logger.error('Session {} failed. :('.format(
                session_friendly_name))
            return SessionStatus.FAIL

        except KeyboardInterrupt:
            logger.error('Session {} interrupted.'.format(
                session_friendly_name))
            raise
