# Copyright 2026 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Create and update conda environments in-process with py-rattler."""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["is_available", "read_spec_file", "sync"]

DEFAULT_CHANNELS = ("conda-forge",)


def __dir__() -> list[str]:
    return __all__


def is_available() -> bool:
    """Return True if py-rattler is importable."""
    return importlib.util.find_spec("rattler") is not None


def _rattler() -> Any:
    try:
        import rattler  # noqa: PLC0415
    except ImportError:
        msg = (
            "The rattler backend needs the py-rattler package. Install Nox with"
            " the `[rattler]` extra, or add `nox[rattler]` to the script"
            " dependencies in script mode."
        )
        raise RuntimeError(msg) from None
    return rattler


def read_spec_file(path: str | os.PathLike[str]) -> list[str]:
    """Read a conda ``--file`` style spec list: one spec per line, ``#`` comments."""
    with open(path, encoding="utf-8") as f:
        lines = (line.split("#", 1)[0].strip() for line in f)
        return [line for line in lines if line]


def _installed_records(rattler: Any, prefix: str) -> list[Any]:
    meta = os.path.join(prefix, "conda-meta")
    if not os.path.isdir(meta):
        return []
    return [
        rattler.PrefixRecord.from_path(os.path.join(meta, name))
        for name in sorted(os.listdir(meta))
        if name.endswith(".json")
    ]


def _requested_specs(records: Sequence[Any]) -> list[str]:
    specs: list[str] = []
    for record in records:
        for spec in record.requested_specs or ():
            if spec not in specs:
                specs.append(spec)
    return specs


def sync(
    prefix: str,
    specs: Sequence[str],
    channels: Sequence[str] = DEFAULT_CHANNELS,
    *,
    offline: bool = False,
) -> None:
    """Add ``specs`` to the requested set of ``prefix`` and bring it up to date.

    Creates the prefix if it does not exist. Specs requested by earlier calls
    are kept, so this behaves like ``conda install --prefix``.
    """
    rattler = _rattler()
    installed = _installed_records(rattler, prefix)
    requested = _requested_specs(installed)
    requested += [spec for spec in specs if spec not in requested]

    gateway = rattler.Gateway(
        default_config=rattler.SourceConfig(
            cache_action="use-cache-only" if offline else "cache-or-fetch"
        )
    )
    match_specs = [rattler.MatchSpec(spec) for spec in requested]

    async def run() -> None:
        records = await rattler.solve(
            list(channels),
            match_specs,
            gateway=gateway,
            virtual_packages=rattler.VirtualPackage.detect(),
            locked_packages=installed,
        )
        await rattler.install(
            records,
            prefix,
            installed_packages=installed,
            show_progress=False,
            # py-rattler 0.25 wants the FFI object here, not the wrapper.
            requested_specs=[getattr(ms, "_match_spec", ms) for ms in match_specs],
        )

    # asyncio logs its selector choice at DEBUG, which Nox's logger shows.
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    asyncio.run(run())
