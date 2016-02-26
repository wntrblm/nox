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

import py

from .command import Command, CommandFailed, FunctionCommand
from .logger import logger
from .virtualenv import VirtualEnv


class SessionConfig(object):
    def __init__(self, posargs=None):
        self.interpreter = None
        self._dependencies = []
        self._commands = []
        self.env = {}
        self._dir = '.'
        self.posargs = posargs or []
        self.reuse_existing_virtualenv = False

    def chdir(self, dir):
        self._dir = dir

    def run(self, *args, **kwargs):
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
        if not args:
            raise ValueError('At least one argument required to install().')
        self._dependencies.append(args)


class Session(object):
    def __init__(self, name, func, global_config):
        self.name = name
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

            elif isinstance(command, FunctionCommand):
                command()

    def execute(self):
        logger.warning('Running session {}'.format(self.name))

        try:
            self._create_config()
            self._create_venv()
            self._install_dependencies()

            if self.config._dir != '.':
                logger.info('Changing directory to {}'.format(self.config._dir))

            cwd = py.path.local(self.config._dir).as_cwd()
            with cwd:
                self._run_commands()

            logger.success('Session {} successful. :)'.format(self.name))
            return True

        except CommandFailed:
            logger.error('Session {} failed. :('.format(self.name))
            return False
