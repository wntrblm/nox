# Copyright 2018 Alethea Katherine Flowers
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

import argparse
import functools
import os
import sys
from typing import Any, List, Optional, Sequence, Union

from nox import _option_set
from nox.tasks import discover_manifest, filter_manifest, load_nox_module

"""All of nox's configuration options."""

options = _option_set.OptionSet(
    description="Nox is a Python automation toolkit.", add_help=False
)

options.add_groups(
    _option_set.OptionGroup(
        "primary",
        "Primary arguments",
        "These are the most common arguments used when invoking Nox.",
    ),
    _option_set.OptionGroup(
        "secondary",
        "Additional arguments & flags",
        "These arguments are used to control Nox's behavior or control advanced features.",
    ),
)


def _session_filters_merge_func(
    key: str, command_args: argparse.Namespace, noxfile_args: argparse.Namespace
) -> List[str]:
    """Only return the Noxfile value for sessions/pythons/keywords if neither sessions,
    pythons or keywords are specified on the command-line.

    Args:
        key (str): This function is used for the "sessions", "pythons" and "keywords"
            options, this allows using ``funtools.partial`` to pass the
            same function for both options.
        command_args (_option_set.Namespace): The options specified on the
            command-line.
        noxfile_args (_option_set.Namespace): The options specified in the
            Noxfile."""
    if not any((command_args.sessions, command_args.pythons, command_args.keywords)):
        return getattr(noxfile_args, key)
    return getattr(command_args, key)


def _default_venv_backend_merge_func(
    command_args: argparse.Namespace, noxfile_args: argparse.Namespace
) -> str:
    """Merge default_venv_backend from command args and nox file. Default is "virtualenv".

    Args:
        command_args (_option_set.Namespace): The options specified on the
            command-line.
        noxfile_Args (_option_set.Namespace): The options specified in the
            Noxfile.
    """
    return (
        command_args.default_venv_backend
        or noxfile_args.default_venv_backend
        or "virtualenv"
    )


def _force_venv_backend_merge_func(
    command_args: argparse.Namespace, noxfile_args: argparse.Namespace
) -> str:
    """Merge force_venv_backend from command args and nox file. Default is None.

    Args:
        command_args (_option_set.Namespace): The options specified on the
            command-line.
        noxfile_Args (_option_set.Namespace): The options specified in the
            Noxfile.
    """
    if command_args.no_venv:
        if (
            command_args.force_venv_backend is not None
            and command_args.force_venv_backend != "none"
        ):
            raise ValueError(
                "You can not use `--no-venv` with a non-none `--force-venv-backend`"
            )
        else:
            return "none"
    else:
        return command_args.force_venv_backend or noxfile_args.force_venv_backend


def _envdir_merge_func(
    command_args: argparse.Namespace, noxfile_args: argparse.Namespace
) -> str:
    """Ensure that there is always some envdir.

    Args:
        command_args (_option_set.Namespace): The options specified on the
            command-line.
        noxfile_Args (_option_set.Namespace): The options specified in the
            Noxfile.
    """
    return command_args.envdir or noxfile_args.envdir or ".nox"


def _sessions_default() -> Optional[List[str]]:
    """Looks at the NOXSESSION env var to set the default value for sessions."""
    nox_env = os.environ.get("NOXSESSION")
    env_sessions = nox_env.split(",") if nox_env else None
    return env_sessions


def _color_finalizer(value: bool, args: argparse.Namespace) -> bool:
    """Figures out the correct value for "color" based on the two color flags.

    Args:
        value (bool): The current value of the "color" option.
        args (_option_set.Namespace): The values for all options.

    Returns:
        The new value for the "color" option.
    """
    if args.forcecolor is True and args.nocolor is True:
        raise _option_set.ArgumentError(
            None, "Can not specify both --no-color and --force-color."
        )

    if args.forcecolor is True:
        return True

    if args.nocolor is True:
        return False

    return sys.stdout.isatty()


def _posargs_finalizer(
    value: Sequence[Any], args: argparse.Namespace
) -> Union[Sequence[Any], List[Any]]:
    """Removes the leading "--"s in the posargs array (if any) and asserts that
    remaining arguments came after a "--".
    """
    posargs = value
    if not posargs:
        return []

    if "--" not in posargs:
        unexpected_posargs = posargs
        raise _option_set.ArgumentError(
            None, "Unknown argument(s) '{}'.".format(" ".join(unexpected_posargs))
        )

    dash_index = posargs.index("--")
    if dash_index != 0:
        unexpected_posargs = posargs[0:dash_index]
        raise _option_set.ArgumentError(
            None, "Unknown argument(s) '{}'.".format(" ".join(unexpected_posargs))
        )

    return posargs[dash_index + 1 :]


def _session_completer(
    prefix: str, parsed_args: argparse.Namespace, **kwargs: Any
) -> List[str]:
    global_config = parsed_args
    module = load_nox_module(global_config)
    manifest = discover_manifest(module, global_config)
    filtered_manifest = filter_manifest(manifest, global_config)
    if isinstance(filtered_manifest, int):
        return []
    return [
        session.friendly_name for session, _ in filtered_manifest.list_all_sessions()
    ]


options.add_options(
    _option_set.Option(
        "help",
        "-h",
        "--help",
        group=options.groups["primary"],
        action="store_true",
        help="Show this help message and exit.",
    ),
    _option_set.Option(
        "version",
        "--version",
        group=options.groups["primary"],
        action="store_true",
        help="Show the Nox version and exit.",
    ),
    _option_set.Option(
        "list_sessions",
        "-l",
        "--list-sessions",
        "--list",
        group=options.groups["primary"],
        action="store_true",
        help="List all available sessions and exit.",
    ),
    _option_set.Option(
        "sessions",
        "-s",
        "-e",
        "--sessions",
        "--session",
        group=options.groups["primary"],
        noxfile=True,
        merge_func=functools.partial(_session_filters_merge_func, "sessions"),
        nargs="*",
        default=_sessions_default,
        help="Which sessions to run. By default, all sessions will run.",
        completer=_session_completer,
    ),
    _option_set.Option(
        "pythons",
        "-p",
        "--pythons",
        "--python",
        group=options.groups["primary"],
        noxfile=True,
        merge_func=functools.partial(_session_filters_merge_func, "pythons"),
        nargs="*",
        help="Only run sessions that use the given python interpreter versions.",
    ),
    _option_set.Option(
        "keywords",
        "-k",
        "--keywords",
        group=options.groups["primary"],
        noxfile=True,
        merge_func=functools.partial(_session_filters_merge_func, "keywords"),
        help="Only run sessions that match the given expression.",
    ),
    _option_set.Option(
        "posargs",
        "posargs",
        group=options.groups["primary"],
        nargs=argparse.REMAINDER,
        help="Arguments following ``--`` that are passed through to the session(s).",
        finalizer_func=_posargs_finalizer,
    ),
    _option_set.Option(
        "verbose",
        "-v",
        "--verbose",
        group=options.groups["secondary"],
        action="store_true",
        help="Logs the output of all commands run including commands marked silent.",
        noxfile=True,
    ),
    _option_set.Option(
        "default_venv_backend",
        "-db",
        "--default-venv-backend",
        group=options.groups["secondary"],
        noxfile=True,
        merge_func=_default_venv_backend_merge_func,
        help="Virtual environment backend to use by default for nox sessions, this is ``'virtualenv'`` by default but "
        "any of ``('virtualenv', 'conda', 'venv')`` are accepted.",
        choices=["none", "virtualenv", "conda", "venv"],
    ),
    _option_set.Option(
        "force_venv_backend",
        "-fb",
        "--force-venv-backend",
        group=options.groups["secondary"],
        noxfile=True,
        merge_func=_force_venv_backend_merge_func,
        help="Virtual environment backend to force-use for all nox sessions in this run, overriding any other venv "
        "backend declared in the nox file and ignoring the default backend. Any of ``('virtualenv', 'conda', 'venv')`` "
        "are accepted.",
        choices=["none", "virtualenv", "conda", "venv"],
    ),
    _option_set.Option(
        "no_venv",
        "--no-venv",
        group=options.groups["secondary"],
        default=False,
        action="store_true",
        help="Runs the selected sessions directly on the current interpreter, without creating a venv. This is an alias "
        "for '--force-venv-backend none'.",
    ),
    *_option_set.make_flag_pair(
        "reuse_existing_virtualenvs",
        ("-r", "--reuse-existing-virtualenvs"),
        ("--no-reuse-existing-virtualenvs",),
        group=options.groups["secondary"],
        help="Re-use existing virtualenvs instead of recreating them.",
    ),
    _option_set.Option(
        "noxfile",
        "-f",
        "--noxfile",
        group=options.groups["secondary"],
        default="noxfile.py",
        help="Location of the Python file containing nox sessions.",
    ),
    _option_set.Option(
        "envdir",
        "--envdir",
        noxfile=True,
        merge_func=_envdir_merge_func,
        group=options.groups["secondary"],
        help="Directory where nox will store virtualenvs, this is ``.nox`` by default.",
    ),
    *_option_set.make_flag_pair(
        "stop_on_first_error",
        ("-x", "--stop-on-first-error"),
        ("--no-stop-on-first-error",),
        group=options.groups["secondary"],
        help="Stop after the first error.",
    ),
    *_option_set.make_flag_pair(
        "error_on_missing_interpreters",
        ("--error-on-missing-interpreters",),
        ("--no-error-on-missing-interpreters",),
        group=options.groups["secondary"],
        help="Error instead of skipping sessions if an interpreter can not be located.",
    ),
    *_option_set.make_flag_pair(
        "error_on_external_run",
        ("--error-on-external-run",),
        ("--no-error-on-external-run",),
        group=options.groups["secondary"],
        help="Error if run() is used to execute a program that isn't installed in a session's virtualenv.",
    ),
    _option_set.Option(
        "install_only",
        "--install-only",
        group=options.groups["secondary"],
        action="store_true",
        help="Skip session.run invocations in the Noxfile.",
    ),
    _option_set.Option(
        "report",
        "--report",
        group=options.groups["secondary"],
        noxfile=True,
        help="Output a report of all sessions to the given filename.",
    ),
    _option_set.Option(
        "non_interactive",
        "--non-interactive",
        group=options.groups["secondary"],
        action="store_true",
        help="Force session.interactive to always be False, even in interactive sessions.",
    ),
    _option_set.Option(
        "nocolor",
        "--nocolor",
        "--no-color",
        group=options.groups["secondary"],
        default=lambda: "NO_COLOR" in os.environ,
        action="store_true",
        help="Disable all color output.",
    ),
    _option_set.Option(
        "forcecolor",
        "--forcecolor",
        "--force-color",
        group=options.groups["secondary"],
        default=False,
        action="store_true",
        help="Force color output, even if stdout is not an interactive terminal.",
    ),
    _option_set.Option(
        "color",
        "--color",
        group=options.groups["secondary"],
        hidden=True,
        finalizer_func=_color_finalizer,
    ),
)


"""Options that are configurable in the Noxfile.

By setting properties on ``nox.options`` you can specify command line
arguments in your Noxfile. If an argument is specified in both the Noxfile
and on the command line, the command line arguments take precedence.

See :doc:`usage` for more details on these settings and their effect.
"""
noxfile_options = options.noxfile_namespace()
