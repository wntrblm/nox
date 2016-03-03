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

import sys

from nox.logger import logger
from nox.popen import popen
import py


class CommandFailed(Exception):
    """Raised when an executed command returns a non-success status code."""
    pass


def which(program, path):
    """Finds the full path to an executable."""
    full_path = None

    if path:
        full_path = py.path.local.sysfind(program, paths=[path])

    if full_path:
        return full_path.strpath

    full_path = py.path.local.sysfind(program)

    if full_path:
        return full_path.strpath

    raise CommandFailed('Program {} not found'.format(program))


class Command(object):
    def __init__(self, args, env=None, silent=False, path=None,
                 success_codes=None):
        self.args = args
        self.silent = silent
        self.env = env
        self.path = path
        self.success_codes = success_codes or [0]

    def run(self):
        cmd, args = self.args[0], self.args[1:]
        full_cmd = ' '.join(self.args)

        logger.info(full_cmd)

        cmd_path = which(cmd, self.path)

        try:
            return_code, output = popen(
                [cmd_path] + list(args),
                silent=self.silent,
                env=self.env)

            if return_code not in self.success_codes:
                logger.error('Command {} failed with exit code {}{}'.format(
                    full_cmd, return_code, ':' if self.silent else ''))

                if self.silent:
                    sys.stderr.write(output)

                raise CommandFailed()

            return output if self.silent else True

        except KeyboardInterrupt as e:
            logger.error('Interrupted...')
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
