# Copyright 2016 Alethea Katherine Flowers
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

"""The nox `main` module.

This is the entrypoint for the ``nox`` command (specifically, the ``main``
function). This module primarily loads configuration, and then passes
control to :meth:``nox.workflow.execute``.
"""

import argparse
import os
import sys

import pkg_resources

from nox import tasks
from nox import workflow
from nox.logger import setup_logging


class GlobalConfig:
    def __init__(self, args):
        self.noxfile = args.noxfile
        self.envdir = os.path.abspath(args.envdir)
        self.sessions = args.sessions
        self.keywords = args.keywords
        self.list_sessions = args.list_sessions
        self.reuse_existing_virtualenvs = args.reuse_existing_virtualenvs
        self.stop_on_first_error = args.stop_on_first_error
        self.error_on_missing_interpreters = args.error_on_missing_interpreters
        self.posargs = args.posargs
        self.report = args.report

        if self.posargs and self.posargs[0] == "--":
            self.posargs.pop(0)


def main():
    parser = argparse.ArgumentParser(description="Nox is a Python automation toolkit.", add_help=False)
    primary = parser.add_argument_group('Primary arguments', "These are the most common arguments used when invoking Nox.")

    primary.add_argument(
        "-h", "--help", action="store_true", help="Show this help message and exit."
    )

    primary.add_argument(
        "--version", action="store_true", help="Show the Nox version and exit."
    )

    primary.add_argument(
        "-l",
        "--list-sessions",
        action="store_true",
        help="List all available sessions and exit.",
    )

    primary.add_argument(
        "-s",
        "-e",
        "--sessions",
        nargs="*",
        default=_get_default_sessions(),
        help="Which sessions to run, by default, all sessions will run.",
    )

    primary.add_argument(
        "-k", "--keywords", help="Only run sessions that match the given expression."
    )

    primary.add_argument(
        "posargs",
        nargs=argparse.REMAINDER,
        help="Arguments following -- that are passed through to the session(s).",
    )

    secondary = parser.add_argument_group('Additional arguments & flags', "These arguments are used to control Nox's behavior or control advanced features.")

    secondary.add_argument(
        "-r",
        "--reuse-existing-virtualenvs",
        action="store_true",
        help="Re-use existing virtualenvs instead of recreating them.",
    )

    secondary.add_argument(
        "-f",
        "--noxfile",
        default="noxfile.py",
        help="Location of the Python file containing nox sessions.",
    )

    secondary.add_argument(
        "--envdir", default=".nox", help="Directory where nox will store virtualenvs."
    )

    secondary.add_argument(
        "-x",
        "--stop-on-first-error",
        action="store_true",
        help="Stop after the first error.",
    )

    secondary.add_argument(
        "--error-on-missing-interpreters",
        action="store_true",
        help="Error instead of skip if an interpreter can not be located.",
    )

    secondary.add_argument(
        "--report", default=None, help="Output a report of all sessions."
    )

    secondary.add_argument(
        "--nocolor",
        default=not sys.stderr.isatty(),
        action="store_true",
        help="Disable all color output.",
    )

    secondary.add_argument(
        "--forcecolor",
        default=False,
        action="store_true",
        help=("Force color output, even if stdout is not an interactive " "terminal."),
    )

    args = parser.parse_args()

    if args.help:
        parser.print_help()
        return

    if args.version:
        dist = pkg_resources.get_distribution("nox")
        print(dist.version, file=sys.stderr)
        return

    global_config = GlobalConfig(args)
    setup_logging(color=not args.nocolor or args.forcecolor)

    # Execute the appropriate tasks.
    exit_code = workflow.execute(
        global_config=global_config,
        workflow=(
            tasks.load_nox_module,
            tasks.discover_manifest,
            tasks.filter_manifest,
            tasks.honor_list_request,
            tasks.verify_manifest_nonempty,
            tasks.run_manifest,
            tasks.print_summary,
            tasks.create_report,
            tasks.final_reduce,
        ),
    )

    # Done; exit.
    sys.exit(exit_code)


def _get_default_sessions():
    nox_env = os.environ.get("NOXSESSION")
    env_sessions = nox_env.split(",") if nox_env else None
    return env_sessions


if __name__ == "__main__":  # pragma: no cover
    main()
