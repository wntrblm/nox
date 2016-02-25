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

from __future__ import print_function

import os
import sys

import sh

from .logger import logger


class CommandFailed(Exception):
    """Raised when an executed command returns a non-success status code."""
    pass


def which(program, path):
    """Finds the full path to an executable, needed by sh."""
    if path:
        venv_path = os.path.join(path, program)

        if os.path.exists(venv_path):
            return venv_path

    return sh.which(program)


class Command(object):
    def __init__(self, args, env=None, silent=False, path=None,
                 success_codes=None):
        self.args = args
        self.silent = silent
        self.env = env
        self.path = path
        self.success_codes = success_codes or [0]

    def run(self):
        full_cmd = ' '.join(self.args)
        logger.info(full_cmd)

        cmd = which(self.args[0], self.path)

        if not cmd:
            logger.error('Command {} not found.'.format(self.args[0]))
            raise CommandFailed('Commmand {} not found'.format(self.args[0]))

        run = sh.Command(cmd)

        args = self.args[1:]
        kwargs = {
            '_env': self.env,
            '_ok_code': self.success_codes
        }

        try:
            if self.silent:
                result = run(*args, **kwargs)
                return result.stdout.decode('utf-8')
            else:
                result = run(*args, _out=sys.stdout, _out_bufsize=0, **kwargs)
                result.wait()
                return True

        except sh.ErrorReturnCode as e:
            logger.error('Command {} failed, exit code {}{}'.format(
                full_cmd, e.exit_code, ':' if self.silent else ''))

            if self.silent:
                sys.stdout.write(e.stdout.decode('utf-8'))
                sys.stderr.write(e.stderr.decode('utf-8'))

            raise CommandFailed(e)

    __call__ = run


class FunctionCommand(object):
    def __init__(self, func):
        self.func = func

    def run(self):
        func_name = self.func.__name__
        logger.info('{}()'.format(func_name))

        try:
            self.func()
            return True
        except Exception as e:
            logger.exception('Function {} raised {}.'.format(
                func_name, e))

            raise CommandFailed(e)

    __call__ = run
