# Copyright 2019 Alethea Katherine Flowers
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

"""Post-parse option policy.

:func:`finalize` resolves alias flags and cross-field options right after
parsing; :func:`merge_noxfile_options` merges values set in the Noxfile into
the config. The generic machinery lives in ``nox._option_set``; the option
model in ``nox._options``.
"""

from __future__ import annotations

__lazy_modules__ = {"nox._option_set"}

import os
import sys
from typing import TYPE_CHECKING

from nox._option_set import ArgumentError, Source, apply_noxfile_values

if TYPE_CHECKING:
    from collections.abc import Sequence

    from nox._options import NoxConfig, NoxfileOptions

__all__ = ["finalize", "merge_noxfile_options"]


def __dir__() -> list[str]:
    return __all__


def _strip_posargs(posargs: Sequence[str]) -> list[str]:
    """Remove the leading "--" from the posargs array (if any) and assert that
    the remaining arguments came after a "--"."""
    if not posargs:
        return []

    dash_index = posargs.index("--") if "--" in posargs else len(posargs)
    if dash_index != 0:
        unexpected_posargs = posargs[:dash_index]
        raise ArgumentError(
            None, f"Unknown argument(s) '{' '.join(unexpected_posargs)}'."
        )

    return list(posargs[dash_index + 1 :])


def finalize(config: NoxConfig) -> None:
    """Resolve aliases and cross-field options after parsing."""
    config.posargs = _strip_posargs(config.posargs)

    if config.force_pythons:
        source = config.provenance("force_pythons")
        config.set_value("pythons", config.force_pythons, source)
        config.set_value("extra_pythons", config.force_pythons, source)

    if config.R:
        # -R wins even over an explicit --reuse-venv (long-standing behavior).
        config.set_value("reuse_venv", "yes", Source.COMMAND_LINE)
        config.set_value("reuse_existing_virtualenvs", True, Source.COMMAND_LINE)  # noqa: FBT003
        config.set_value("no_install", True, Source.COMMAND_LINE)  # noqa: FBT003

    # -r/-N are an alias for --reuse-venv=yes|no; an explicit --reuse-venv wins.
    if (
        config.reuse_existing_virtualenvs is not None
        and config.provenance("reuse_venv") is not Source.COMMAND_LINE
    ):
        config.set_value(
            "reuse_venv",
            "yes" if config.reuse_existing_virtualenvs else "no",
            Source.COMMAND_LINE,
        )

    if config.no_venv:
        if config.force_venv_backend not in {None, "none"}:
            msg = "You can not use `--no-venv` with a non-none `--force-venv-backend`"
            raise ValueError(msg)
        config.set_value("force_venv_backend", "none", Source.COMMAND_LINE)

    if config.forcecolor and config.nocolor:
        raise ArgumentError(None, "Can not specify both --no-color and --force-color.")
    config.color = config.forcecolor or (not config.nocolor and sys.stdout.isatty())


def merge_noxfile_options(config: NoxConfig, noxfile_config: NoxfileOptions) -> None:
    """Apply ``nox.options`` (as set by the noxfile) to the parsed config.

    A value explicitly given on the command line (or via an environment
    variable) always wins over the noxfile.
    """
    # sessions/keywords/tags are only taken from the noxfile if none of the
    # three was given on the command line.
    trio = ("sessions", "keywords", "tags")
    cli_selected = any(config.provenance(name) is not Source.DEFAULT for name in trio)
    apply_noxfile_values(config, noxfile_config, skip=trio if cli_selected else ())

    # The legacy reuse_existing_virtualenvs alias, when enabled in the
    # noxfile, wins over a noxfile-set reuse_venv (but not the command line).
    if (
        noxfile_config.provenance("reuse_existing_virtualenvs") is not Source.DEFAULT
        and noxfile_config.reuse_existing_virtualenvs
        and config.provenance("reuse_venv") is not Source.COMMAND_LINE
    ):
        config.set_value("reuse_venv", "yes", Source.NOXFILE)

    # The noxfile may have set a PathLike envdir.
    config.envdir = os.fspath(config.envdir)
