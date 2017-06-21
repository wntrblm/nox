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

import py
import six

from nox.logger import logger
from nox.popen import popen
from nox.utils import coerce_str


class CommandFailed(Exception):
    """Raised when an executed command returns a non-success status code."""
    def __init__(self, reason=None):
        super(CommandFailed, self).__init__(reason)
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

    logger.error('Program {} not found.'.format(program))
    raise CommandFailed('Program {} not found'.format(program))


class Command(object):
    def __init__(self, args, env=None, silent=False, path=None,
                 success_codes=None):
        self.args = args
        self.silent = silent
        self.env = env
        self.path = path
        self.success_codes = success_codes or [0]

    def run(self, path_override=None, env_fallback=None):
        path = self.path if path_override is None else path_override

        env = env_fallback.copy() if env_fallback is not None else None
        if self.env is not None:
            if env is None:
                env = self.env
            else:
                env.update(self.env)

        cmd, args = self.args[0], self.args[1:]
        full_cmd = ' '.join(self.args)

        logger.info(full_cmd)

        cmd_path = which(cmd, path)

        # Environment variables must be the "str" type.
        # In other words, they must be bytestrings in Python 2, and Unicode
        # text strings in Python 3.
        clean_env = {} if env is not None else None
        if clean_env is not None:
            # Ensure systemroot is passed down, otherwise Windows will explode.
            clean_env[str('SYSTEMROOT')] = os.environ.get(
                'SYSTEMROOT', str(''))

            for key, value in six.iteritems(env):
                key = coerce_str(key)
                value = coerce_str(value)
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
    def __init__(self, func, args=None, kwargs=None, debug=False):
        self.func = func
        self.debug = debug
        self.args = args or ()
        self.kwargs = kwargs or {}
        try:
            self._func_name = self.func.__name__
        except AttributeError:
            self._func_name = '{!r}'.format(self.func)

    def run(self):
        if self.debug:
            logger.debug(str(self))
        else:
            logger.info(str(self))

        try:
            self.func(*self.args, **self.kwargs)
            return True
        except Exception as e:
            logger.exception('Function {} raised {}.'.format(
                self._func_name, e))

            raise CommandFailed(e)

    __call__ = run

    def __str__(self):
        return '{}(args={!r}, kwargs={!r})'.format(
            self._func_name, self.args, self.kwargs)


class ChdirCommand(FunctionCommand):
    def __init__(self, path, debug=False):
        self.path = path
        super(ChdirCommand, self).__init__(os.chdir, args=(self.path,),
                                           debug=debug)

    def __str__(self):
        return 'chdir {}'.format(self.path)


class InstallCommand(object):
    def __init__(self, deps):
        self.deps = deps

    def run(self, venv):
        venv.install(*self.deps)

    __call__ = run

    def __str__(self):
        return ' '.join(self.deps)
