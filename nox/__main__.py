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


def _default_with_off_flag(current, default, off_flag):
    """Helper method for merging command line args and noxfile config.

    Returns False if off_flag is set, otherwise, returns the default value if
    set, otherwise, returns the current value.
    """
    return (default or current) and not off_flag


class GlobalConfig:
    def __init__(self, args):
        self.noxfile = args.noxfile
        self.envdir = args.envdir
        self.sessions = args.sessions
        self.keywords = args.keywords
        self.list_sessions = args.list_sessions
        self.reuse_existing_virtualenvs = args.reuse_existing_virtualenvs
        self.no_reuse_existing_virtualenvs = args.no_reuse_existing_virtualenvs
        self.stop_on_first_error = args.stop_on_first_error
        self.no_stop_on_first_error = args.no_stop_on_first_error
        self.error_on_missing_interpreters = args.error_on_missing_interpreters
        self.no_error_on_missing_interpreters = args.no_error_on_missing_interpreters
        self.error_on_external_run = args.error_on_external_run
        self.no_error_on_external_run = args.no_error_on_external_run
        self.install_only = args.install_only
        self.posargs = args.posargs
        self.report = args.report

        if self.posargs and self.posargs[0] == "--":
            self.posargs.pop(0)

    def merge_from_options(self, options):
        """Update the config from the Noxfile-specified options.

        The options function as "defaults" for the most part, with some small
        caveats documented in the body of the function.

        Args:
            options (nox._options.options): The options set in the Noxfile.
        """
        # If *either* sessions or keywords are specified on the command line,
        # ignore *both* sessions and keywords in Noxfile.
        if not self.sessions and not self.keywords:
            self.sessions = options.sessions
            self.keywords = options.keywords

        self.envdir = self.envdir or options.envdir or ".nox"
        self.reuse_existing_virtualenvs = _default_with_off_flag(
            self.reuse_existing_virtualenvs,
            options.reuse_existing_virtualenvs,
            self.no_reuse_existing_virtualenvs,
        )
        self.stop_on_first_error = _default_with_off_flag(
            self.stop_on_first_error,
            options.stop_on_first_error,
            self.no_stop_on_first_error,
        )
        self.error_on_missing_interpreters = _default_with_off_flag(
            self.error_on_missing_interpreters,
            options.error_on_missing_interpreters,
            self.no_error_on_missing_interpreters,
        )
        self.error_on_external_run = _default_with_off_flag(
            self.error_on_external_run,
            options.error_on_external_run,
            self.no_error_on_external_run,
        )
        self.report = self.report or options.report


def main():
    parser = argparse.ArgumentParser(
        description="Nox is a Python automation toolkit.", add_help=False
    )
    primary = parser.add_argument_group(
        "Primary arguments",
        "These are the most common arguments used when invoking Nox.",
    )

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

    secondary = parser.add_argument_group(
        "Additional arguments & flags",
        "These arguments are used to control Nox's behavior or control advanced features.",
    )

    secondary.add_argument(
        "-r",
        "--reuse-existing-virtualenvs",
        action="store_true",
        help="Re-use existing virtualenvs instead of recreating them.",
    )
    secondary.add_argument(
        "--no-reuse-existing-virtualenvs",
        action="store_true",
        help="Disables --reuse-existing-virtualenvs if it is enabled in the Noxfile.",
    )

    secondary.add_argument(
        "-f",
        "--noxfile",
        default="noxfile.py",
        help="Location of the Python file containing nox sessions.",
    )

    secondary.add_argument(
        "--envdir",
        help="Directory where nox will store virtualenvs, this is .nox by default.",
    )

    secondary.add_argument(
        "-x",
        "--stop-on-first-error",
        action="store_true",
        help="Stop after the first error.",
    )
    secondary.add_argument(
        "--no-stop-on-first-error",
        action="store_true",
        help="Disables --stop-on-first-error if it is enabled in the Noxfile.",
    )

    secondary.add_argument(
        "--error-on-missing-interpreters",
        action="store_true",
        help="Error instead of skip if an interpreter can not be located.",
    )
    secondary.add_argument(
        "--no-error-on-missing-interpreters",
        action="store_true",
        help="Disables --error-on-missing-interpreters if it is enabled in the Noxfile.",
    )

    secondary.add_argument(
        "--error-on-external-run",
        action="store_true",
        help="Error if run() is used to execute a program that isn't installed in a session's virtualenv.",
    )
    secondary.add_argument(
        "--no-error-on-external-run",
        action="store_true",
        help="Disables --error-on-external-run if it is enabled in the Noxfile.",
    )

    secondary.add_argument(
        "--install-only",
        action="store_true",
        help="Skip session.run invocations in the Noxfile.",
    )

    secondary.add_argument(
        "--report", help="Output a report of all sessions to the given filename."
    )

    secondary.add_argument(
        "--nocolor",
        default="NO_COLOR" in os.environ or not sys.stderr.isatty(),
        action="store_true",
        help="Disable all color output.",
    )

    secondary.add_argument(
        "--forcecolor",
        default=False,
        action="store_true",
        help="Force color output, even if stdout is not an interactive terminal.",
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
            tasks.merge_noxfile_options,
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
