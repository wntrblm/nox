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

"""All of Nox's configuration options, defined once as typed attrs classes."""

from __future__ import annotations

__lazy_modules__ = {"argparse", "nox._option_set", "nox.virtualenv"}

import argparse
import os
from typing import TYPE_CHECKING, Any, Literal

import attrs
import attrs.validators as av

from nox import _completers, _merge, _option_set
from nox._option_set import opt
from nox.virtualenv import ALL_VENVS

if TYPE_CHECKING:
    from collections.abc import Callable

    # Opaque validator type; keeps mypy's attrs plugin from inferring field
    # types from the validator instead of the annotation.
    Validator = Callable[[Any, "attrs.Attribute[Any]", Any], Any]


__all__ = [
    "NoxConfig",
    "NoxfileOptions",
    "ReuseVenvType",
    "noxfile_options",
    "options",
]


def __dir__() -> list[str]:
    return __all__


ReuseVenvType = Literal["no", "yes", "never", "always"]

av_str: Validator = av.instance_of(str)
av_opt_str: Validator = av.optional(av.instance_of(str))
av_path: Validator = av.or_(
    av.instance_of(str),
    av.instance_of(os.PathLike),  # type: ignore[type-abstract]
)
av_opt_list_str: Validator = av.optional(
    av.deep_iterable(
        member_validator=av.instance_of(str),
        iterable_validator=av.not_(av.instance_of(str)),
    )
)
av_opt_bool: Validator = av.optional(av.instance_of(bool))
av_bool: Validator = av.instance_of(bool)

GROUPS: dict[str, tuple[str, str]] = {
    "general": (
        "General options",
        "These are general arguments used when invoking Nox.",
    ),
    "sessions": (
        "Sessions options",
        "These arguments are used to control which Nox session(s) to execute.",
    ),
    "python": (
        "Python options",
        "These arguments are used to control which Python version(s) to use.",
    ),
    "environment": (
        "Environment options",
        "These arguments are used to control Nox's creation and usage of virtual"
        " environments.",
    ),
    "execution": (
        "Execution options",
        "These arguments are used to control execution of sessions.",
    ),
    "reporting": (
        "Reporting options",
        "These arguments are used to control Nox's reporting during execution.",
    ),
}


def _error_on_missing_interpreters_default() -> bool:
    return "CI" in os.environ


def _nocolor_default() -> bool:
    return "NO_COLOR" in os.environ


def _forcecolor_default() -> bool:
    return os.environ.get("FORCE_COLOR", "").lower() not in {
        "",
        "0",
        "false",
        "no",
        "off",
    }


@attrs.define(
    kw_only=True,
    on_setattr=[attrs.setters.validate, _option_set.record_noxfile_set],
)
class NoxfileOptions(_option_set.OptionsBase):
    """Options that are configurable in the Noxfile.

    By setting properties on ``nox.options`` you can specify command line
    arguments in your Noxfile. If an argument is specified in both the Noxfile
    and on the command line, the command line arguments take precedence.

    See :doc:`usage` for more details on these settings and their effect.
    """

    default_venv_backend: str = attrs.field(
        default="virtualenv",
        validator=av_str,
        metadata=opt(
            "-db",
            "--default-venv-backend",
            group="environment",
            env_var="NOX_DEFAULT_VENV_BACKEND",
            argparse_kwargs={"choices": list(ALL_VENVS)},
            help=(
                "Virtual environment backend to use by default for Nox sessions, this is"
                f" ``'virtualenv'`` by default but any of ``{list(ALL_VENVS)!r}`` are accepted."
            ),
        ),
    )
    download_python: Literal["auto", "never", "always"] | None = attrs.field(
        default=None,
        validator=av.optional(av.in_(["auto", "never", "always"])),
        metadata=opt(
            "--download-python",
            group="python",
            env_var="NOX_DOWNLOAD_PYTHON",
            help=(
                "When should nox download python standalone builds to run the sessions,"
                " defaults to 'auto' which will download when the version requested can't"
                " be found in the running environment. Environment variable: NOX_DOWNLOAD_PYTHON"
            ),
        ),
    )
    envdir: str | os.PathLike[str] = attrs.field(
        default=".nox",
        validator=av_path,
        metadata=opt(
            "--envdir",
            group="environment",
            completer=_completers.directory_completer,
            help="Directory where Nox will store virtualenvs, this is ``.nox`` by default.",
        ),
    )
    error_on_external_run: bool = attrs.field(
        default=False,
        validator=av_bool,
        metadata=opt(
            "--error-on-external-run",
            negative_flags=("--no-error-on-external-run",),
            group="execution",
            help=(
                "Error if run() is used to execute a program that isn't installed in a"
                " session's virtualenv."
            ),
        ),
    )
    error_on_missing_interpreters: bool = attrs.field(
        default=attrs.Factory(_error_on_missing_interpreters_default),
        validator=av_bool,
        metadata=opt(
            "--error-on-missing-interpreters",
            negative_flags=("--no-error-on-missing-interpreters",),
            group="execution",
            help="Error instead of skipping sessions if an interpreter can not be located.",
        ),
    )
    force_venv_backend: str | None = attrs.field(
        default=None,
        validator=av_opt_str,
        metadata=opt(
            "-fb",
            "--force-venv-backend",
            group="environment",
            argparse_kwargs={"choices": list(ALL_VENVS)},
            help=(
                "Virtual environment backend to force-use for all Nox sessions in this run,"
                " overriding any other venv backend declared in the Noxfile and ignoring"
                f" the default backend. Any of ``{list(ALL_VENVS)!r}`` are accepted."
            ),
        ),
    )
    keywords: str | None = attrs.field(
        default=None,
        validator=av_opt_str,
        metadata=opt(
            "-k",
            "--keywords",
            group="sessions",
            completer=_completers.empty_completer,
            help="Only run sessions that match the given expression.",
        ),
    )
    pythons: list[str] | None = attrs.field(
        default=None,
        validator=av_opt_list_str,
        metadata=opt(
            "-p",
            "--pythons",
            "--python",
            group="python",
            env_var="NOXPYTHON",
            completer=_completers.python_completer,
            help=(
                "Only run sessions that use the given python interpreter versions."
                " Environment variable: NOXPYTHON"
            ),
        ),
    )
    report: str | None = attrs.field(
        default=None,
        validator=av_opt_str,
        metadata=opt(
            "--report",
            group="reporting",
            completer=_completers.json_file_completer,
            help="Output a report of all sessions to the given filename.",
        ),
    )
    reuse_existing_virtualenvs: bool | None = attrs.field(
        default=None,
        validator=av_opt_bool,
        metadata=opt(
            "-r",
            "--reuse-existing-virtualenvs",
            negative_flags=("-N", "--no-reuse-existing-virtualenvs"),
            group="environment",
            help="This is an alias for '--reuse-venv=yes|no'.",
        ),
    )
    reuse_venv: ReuseVenvType = attrs.field(
        default="no",
        validator=av.in_(["no", "yes", "never", "always"]),
        metadata=opt(
            "--reuse-venv",
            group="environment",
            help=(
                "Controls existing virtualenvs recreation. This is ``'no'`` by"
                " default, but any of ``('yes', 'no', 'always', 'never')`` are accepted."
            ),
        ),
    )
    sessions: list[str] | None = attrs.field(
        default=None,
        validator=av_opt_list_str,
        metadata=opt(
            "-s",
            "-e",
            "--sessions",
            "--session",
            group="sessions",
            env_var="NOXSESSION",
            completer=_completers.session_completer,
            help=(
                "Which sessions to run. By default, all sessions will run."
                " Environment variable: NOXSESSION"
            ),
        ),
    )
    stop_on_first_error: bool = attrs.field(
        default=False,
        validator=av_bool,
        metadata=opt(
            "-x",
            "--stop-on-first-error",
            negative_flags=("--no-stop-on-first-error",),
            group="execution",
            help="Stop after the first error.",
        ),
    )
    tags: list[str] | None = attrs.field(
        default=None,
        validator=av_opt_list_str,
        metadata=opt(
            "-t",
            "--tags",
            group="sessions",
            completer=_completers.tag_completer,
            help="Only run sessions with the given tags.",
        ),
    )
    verbose: bool = attrs.field(
        default=False,
        validator=av_bool,
        metadata=opt(
            "-v",
            "--verbose",
            negative_flags=("--no-verbose",),
            group="reporting",
            help="Logs the output of all commands run including commands marked silent.",
        ),
    )


@attrs.define(kw_only=True, on_setattr=attrs.setters.validate)
class NoxConfig(NoxfileOptions):
    """The full configuration: every CLI option, including the noxfile-settable
    ones inherited from :class:`NoxfileOptions`.

    An instance of this class is the ``global_config`` threaded through the
    workflow tasks and sessions.
    """

    help: bool = attrs.field(
        default=False,
        metadata=opt(
            "-h",
            "--help",
            group="general",
            help="Show this help message and exit.",
        ),
    )
    version: bool = attrs.field(
        default=False,
        metadata=opt(
            "--version",
            group="general",
            help="Show the Nox version and exit.",
        ),
    )
    script_mode: Literal["none", "fresh", "reuse"] = attrs.field(
        default="reuse",
        metadata=opt("--script-mode", group="general"),
    )
    script_venv_backend: str | None = attrs.field(
        default=None,
        metadata=opt("--script-venv-backend", group="general"),
    )
    noxfile: str = attrs.field(
        default="noxfile.py",
        metadata=opt(
            "-f",
            "--noxfile",
            group="general",
            help="Location of the Python file containing Nox sessions.",
        ),
    )
    posargs: list[str] = attrs.field(
        factory=list,
        metadata=opt(
            group="general",
            positional=True,
            argparse_kwargs={"nargs": argparse.REMAINDER},
            help="Arguments following ``--`` that are passed through to the session(s).",
        ),
    )
    list_sessions: bool = attrs.field(
        default=False,
        metadata=opt(
            "-l",
            "--list-sessions",
            "--list",
            group="sessions",
            help="List all available sessions and exit.",
        ),
    )
    usage: list[str] | None = attrs.field(
        default=None,
        metadata=opt(
            "--usage",
            group="sessions",
            argparse_kwargs={"nargs": 1},
            help="Print the full docstring of a given session and exit. Raises if there is no docstring.",
        ),
    )
    json: bool = attrs.field(
        default=False,
        metadata=opt(
            "--json",
            group="sessions",
            help="JSON output formatting. Requires list-sessions currently.",
        ),
    )
    extra_pythons: list[str] | None = attrs.field(
        default=None,
        metadata=opt(
            "--extra-pythons",
            "--extra-python",
            group="python",
            env_var="NOXEXTRAPYTHON",
            completer=_completers.python_completer,
            help=(
                "Additionally, run sessions using the given python interpreter versions."
                " Environment variable: NOXEXTRAPYTHON"
            ),
        ),
    )
    force_pythons: list[str] | None = attrs.field(
        default=None,
        metadata=opt(
            "-P",
            "--force-pythons",
            "--force-python",
            group="python",
            env_var="NOXFORCEPYTHON",
            completer=_completers.python_completer,
            help=(
                "Run sessions with the given interpreters instead of those listed in the"
                " Noxfile. This is a shorthand for ``--python=X.Y --extra-python=X.Y``."
                " It will also work on sessions that don't have any interpreter parametrized."
                " Environment variable: NOXFORCEPYTHON"
            ),
        ),
    )
    no_venv: bool = attrs.field(
        default=False,
        metadata=opt(
            "--no-venv",
            group="environment",
            help=(
                "Runs the selected sessions directly on the current interpreter, without"
                " creating a venv. This is an alias for '--force-venv-backend none'."
            ),
        ),
    )
    R: bool = attrs.field(
        default=False,
        metadata=opt(
            "-R",
            group="environment",
            help=(
                "Reuse existing virtualenvs and skip package re-installation."
                " This is an alias for '--reuse-existing-virtualenvs --no-install'."
            ),
        ),
    )
    install_only: bool = attrs.field(
        default=False,
        metadata=opt(
            "--install-only",
            group="execution",
            help="Skip session.run invocations in the Noxfile.",
        ),
    )
    no_install: bool = attrs.field(
        default=False,
        metadata=opt(
            "--no-install",
            group="execution",
            help=(
                "Skip invocations of session methods for installing packages"
                " (session.install, session.conda_install, session.run_install)"
                " when a virtualenv is being reused."
            ),
        ),
    )
    non_interactive: bool = attrs.field(
        default=False,
        metadata=opt(
            "--non-interactive",
            group="execution",
            help=(
                "Force session.interactive to always be False, even in interactive"
                " sessions."
            ),
        ),
    )
    add_timestamp: bool = attrs.field(
        default=False,
        metadata=opt(
            "-ts",
            "--add-timestamp",
            group="reporting",
            help="Adds a timestamp to logged output.",
        ),
    )
    nocolor: bool = attrs.field(
        default=attrs.Factory(_nocolor_default),
        metadata=opt(
            "--nocolor",
            "--no-color",
            group="reporting",
            help="Disable all color output. Environment variable: NO_COLOR",
        ),
    )
    forcecolor: bool = attrs.field(
        default=attrs.Factory(_forcecolor_default),
        metadata=opt(
            "--forcecolor",
            "--force-color",
            group="reporting",
            help="Force color output, even if stdout is not an interactive terminal.",
        ),
    )
    color: bool = attrs.field(default=False, metadata=opt(hidden=True))
    # The original working directory that Nox was invoked from, since it could
    # be different from the Noxfile's directory.
    invoked_from: str = attrs.field(
        default=attrs.Factory(os.getcwd),
        metadata=opt(hidden=True),
    )


options = _option_set.Options(
    NoxConfig,
    groups=GROUPS,
    description="Nox is a Python automation toolkit.",
    finalize=_merge.finalize,
)

noxfile_options: NoxfileOptions = NoxfileOptions()
"""The ``nox.options`` object noxfiles mutate to configure Nox."""
