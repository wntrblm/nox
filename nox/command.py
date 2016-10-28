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

from nox.logger import logger
from nox.popen import popen
import py
import six


class CommandFailed(Exception):
    """Raised when an executed command returns a non-success status code."""
    def __init__(self, reason=None):
        super(CommandFailed, self).__init__()
        self.reason = reason


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

        # Environment variables must be bytestrings.
        clean_env = {} if self.env is not None else None
        if clean_env is not None:
            # Ensure systemroot is passed down, otherwise Windows will explode.
            clean_env[str('SYSTEMROOT')] = os.environ.get(
                'SYSTEMROOT', str(''))

            for key, value in six.iteritems(self.env):
                if not isinstance(key, six.text_type):
                    key = key.decode('utf-8')
                if not isinstance(value, six.text_type):
                    value = value.decode('utf-8')
                clean_env[key] = value

        try:
            return_code, output = popen(
                [cmd_path] + list(args),
                silent=self.silent,
                env=clean_env)

            if return_code not in self.success_codes:
                logger.error('Command {} failed with exit code {}{}'.format(
                    full_cmd, return_code, ':' if self.silent else ''))

                if self.silent:
                    sys.stderr.write(output)

                raise CommandFailed('Returned code {}'.format(return_code))

            return output if self.silent else True

        except KeyboardInterrupt:
            logger.error('Interrupted...')
            raise

    __call__ = run


class FunctionCommand(object):
    def __init__(self, func, args=None, kwargs=None):
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}

    def run(self):
        try:
            func_name = self.func.__name__
        except AttributeError:
            func_name = '{!r}'.format(self.func)

        logger.info('{}(args={!r}, kwargs={!r})'.format(
            func_name, self.args, self.kwargs))

        try:
            self.func(*self.args, **self.kwargs)
            return True
        except Exception as e:
            logger.exception('Function {} raised {}.'.format(
                func_name, e))

            raise CommandFailed(e)

    __call__ = run
