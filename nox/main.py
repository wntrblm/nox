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

import argparse
import imp
from inspect import isfunction
import os
import sys

from six import iteritems

from .logger import setup_logging
from .session import Session


class GlobalConfig(object):
    def __init__(self, args):
        self.noxfile = args.noxfile
        self.envdir = os.path.abspath(args.envdir)
        self.sessions = args.sessions
        self.reuse_existing_virtualenvs = args.reuse_existing_virtualenvs
        self.stop_on_first_error = args.stop_on_first_error
        self.posargs = args.posargs

        if self.posargs and self.posargs[0] == '--':
            self.posargs.pop(0)


def load_user_nox_module(module_file_name='nox.py'):
    module = imp.load_source('user_nox_module', module_file_name)
    return module


def discover_session_functions(module):
    funcs = []
    for name, obj in iteritems(module.__dict__):
        if name.startswith('session_') and isfunction(obj):
            funcs.append((name.split('session_', 1).pop(), obj))
    return sorted(funcs)


def make_sessions(session_functions, global_config):
    sessions = []
    for name, func in session_functions:
        sessions.append(Session(name, func, global_config))
    return sessions


def run(global_config):
    user_nox_module = load_user_nox_module(global_config.noxfile)
    session_functions = discover_session_functions(user_nox_module)
    sessions = make_sessions(session_functions, global_config)

    if global_config.sessions:
        sessions = [x for x in sessions if x.name in global_config.sessions]

    success = True

    for session in sessions:
        result = session.execute()
        success = success and result
        if not success and global_config.stop_on_first_error:
            return False

    return success


def main():
    parser = argparse.ArgumentParser(
        description='nox is a Python automation toolkit.')
    parser.add_argument(
        '-f', '--noxfile', default='nox.py',
        help='Location of the Python file containing nox sessions.')
    parser.add_argument(
        '--envdir', default='.nox',
        help='Directory where nox will store virtualenvs.')
    parser.add_argument(
        '-s', '-e', '--sessions', nargs='*',
        help='Which sessions to run, by default, all sessions will run.')
    parser.add_argument(
        '-r', '--reuse-existing-virtualenvs', action='store_true',
        help='Re-use existing virtualenvs instead of recreating them.')
    parser.add_argument(
        '--stop-on-first-error', action='store_true',
        help='Stop after the first error.')
    parser.add_argument(
        'posargs', nargs=argparse.REMAINDER,
        help='Arguments that are passed through to the sessions.')

    args = parser.parse_args()
    global_config = GlobalConfig(args)

    setup_logging()

    success = run(global_config)

    if not success:
        sys.exit(1)
