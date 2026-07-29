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

"""Shell completion (argcomplete) helpers for Nox's command-line options."""

from __future__ import annotations

__lazy_modules__ = {"itertools", "nox.tasks"}

import itertools
from typing import TYPE_CHECKING, Any

import argcomplete.completers

from nox.tasks import discover_manifest, filter_manifest, load_nox_module

if TYPE_CHECKING:
    import argparse
    from collections.abc import Iterable

    from nox._options import NoxConfig

__all__ = [
    "directory_completer",
    "empty_completer",
    "json_file_completer",
    "python_completer",
    "session_completer",
    "tag_completer",
]


def __dir__() -> list[str]:
    return __all__


directory_completer: argcomplete.completers.DirectoriesCompleter = (
    argcomplete.completers.DirectoriesCompleter()  # type: ignore[no-untyped-call]
)
json_file_completer: argcomplete.completers.FilesCompleter = (
    argcomplete.completers.FilesCompleter(("json",))  # type: ignore[no-untyped-call]
)
empty_completer: argcomplete.completers.ChoicesCompleter = (
    argcomplete.completers.ChoicesCompleter(())  # type: ignore[no-untyped-call]
)


def _expand(parsed_args: argparse.Namespace | NoxConfig) -> NoxConfig:
    # Imported here: nox._options needs this module to define its fields.
    from nox._options import options  # noqa: PLC0415

    return options.expand(parsed_args)


def python_completer(
    prefix: str,  # noqa: ARG001
    parsed_args: argparse.Namespace | NoxConfig,
    **kwargs: Any,
) -> Iterable[str]:
    config = _expand(parsed_args)
    module = load_nox_module(config)
    manifest = discover_manifest(module, config)
    return filter(
        None,
        (
            session.func.python  # type:ignore[misc] # str sequences flattened, other non-strs falsey and filtered out
            for session, _ in manifest.list_all_sessions()
        ),
    )


def session_completer(
    prefix: str,  # noqa: ARG001
    parsed_args: argparse.Namespace | NoxConfig,
    **kwargs: Any,
) -> Iterable[str]:
    config = _expand(parsed_args)
    config.list_sessions = True
    module = load_nox_module(config)
    manifest = discover_manifest(module, config)
    filtered_manifest = filter_manifest(manifest, config)
    if isinstance(filtered_manifest, int):
        return []
    return (
        session.friendly_name for session, _ in filtered_manifest.list_all_sessions()
    )


def tag_completer(
    prefix: str,  # noqa: ARG001
    parsed_args: argparse.Namespace | NoxConfig,
    **kwargs: Any,
) -> Iterable[str]:
    config = _expand(parsed_args)
    module = load_nox_module(config)
    manifest = discover_manifest(module, config)
    return itertools.chain.from_iterable(
        filter(None, (session.tags for session, _ in manifest.list_all_sessions()))
    )
