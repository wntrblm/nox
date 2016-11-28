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
import itertools
import os
import sys

from nox._parametrize import generate_calls
from nox.logger import logger, setup_logging
from nox.session import Session
from six import iteritems


class GlobalConfig(object):
    def __init__(self, args):
        self.noxfile = args.noxfile
        self.envdir = os.path.abspath(args.envdir)
        self.sessions = args.sessions
        self.list_sessions = args.list_sessions
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


def _null_session_func(session):
    session.virtualenv = False

    def empty_session():
        print('This session had no parameters available.')

    session.run(empty_session)


def make_sessions(session_functions, global_config):
    sessions = []
    for name, func in session_functions:
        if not hasattr(func, 'parametrize'):
            sessions.append(Session(name, None, func, global_config))
        else:
            calls = generate_calls(func, func.parametrize)
            for call in calls:
                session = Session(
                    name, name + call.session_signature, call, global_config)
                sessions.append(session)
            if not calls:
                # Add an empty, do-nothing session.
                sessions.append(Session(
                    name, None, _null_session_func, global_config))

    return sessions


def filter_sessions(specified_sessions, available_sessions):
    sessions = [x for x in available_sessions if (
        x.name in specified_sessions or
        x.signature in specified_sessions)]
    missing_sessions = set(specified_sessions) - set(
        itertools.chain(
            [x.name for x in sessions if x.name],
            [x.signature for x in sessions if x.signature]))
    if missing_sessions:
        logger.error('Sessions {} not found.'.format(', '.join(
            missing_sessions)))
        return False

    return sessions


def print_summary(results):
    logger.warning('Ran multiple sessions:')
    for session, result in results:
        log = logger.success if result else logger.error
        log('* {}: {}'.format(
            session, 'passed' if result else 'failed'))


def run(global_config):
    try:
        user_nox_module = load_user_nox_module(global_config.noxfile)
    except IOError:
        logger.error('Noxfile {} not found.'.format(global_config.noxfile))
        return False

    session_functions = discover_session_functions(user_nox_module)
    sessions = make_sessions(session_functions, global_config)

    if global_config.list_sessions:
        print('Available sessions:')
        for session in sessions:
            print('*', session.signature or session.name)
        return True

    if global_config.sessions:
        sessions = filter_sessions(global_config.sessions, sessions)

    if not sessions:
        return False

    success = True
    results = []

    for session in sessions:
        result = session.execute()
        results.append((session.signature or session.name, result))
        success = success and result
        if not success and global_config.stop_on_first_error:
            success = False
            break

    if len(results) > 1:
        print_summary(results)

    return success


def main():
    parser = argparse.ArgumentParser(
        description='nox is a Python automation toolkit.')
    parser.add_argument(
        '-f', '--noxfile', default='nox.py',
        help='Location of the Python file containing nox sessions.')
    parser.add_argument(
        '-l', '--list-sessions', action='store_true',
        help='List all available sessions and exit.')
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

    try:
        success = run(global_config)
    except KeyboardInterrupt:
        success = False

    if not success:
        sys.exit(1)
