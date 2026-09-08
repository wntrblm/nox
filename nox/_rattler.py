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

__lazy_modules__ = {"importlib", "importlib.util", "pathlib"}

import functools
import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import os
    from collections.abc import Sequence

__all__ = ["is_available", "read_spec_file", "sync"]


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


@functools.cache
def _gateway(*, offline: bool) -> Any:
    """One Gateway per process so repodata is loaded once."""
    rattler = _rattler()
    return rattler.Gateway(
        default_config=rattler.SourceConfig(
            cache_action="use-cache-only" if offline else "cache-or-fetch"
        )
    )


def read_spec_file(path: str | os.PathLike[str]) -> list[str]:
    """Read a conda ``--file`` style spec list: one spec per line, ``#`` comments."""
    with open(path, encoding="utf-8") as f:
        lines = (line.split("#", 1)[0].strip() for line in f)
        return [line for line in lines if line]


def sync(
    prefix: str,
    specs: Sequence[str],
    channels: Sequence[str],
    *,
    offline: bool = False,
) -> None:
    """Add ``specs`` to the requested set of ``prefix`` and bring it up to date.

    Creates the prefix if it does not exist. Specs requested by earlier calls
    are kept unless the same package is requested again, so this behaves like
    ``conda install --prefix``.
    """
    import asyncio  # noqa: PLC0415

    rattler = _rattler()
    installed = [
        rattler.PrefixRecord.from_path(path)
        for path in sorted(Path(prefix, "conda-meta").glob("*.json"))
    ]
    # Keyed by package name so a new request replaces the historical one.
    requested = {
        ms.name.normalized: ms
        for spec in (
            *(s for record in installed for s in record.requested_specs or ()),
            *specs,
        )
        for ms in (rattler.MatchSpec(spec),)
    }
    match_specs = list(requested.values())

    async def run() -> None:
        records = await rattler.solve(
            list(channels),
            match_specs,
            gateway=_gateway(offline=offline),
            virtual_packages=rattler.VirtualPackage.detect(),
            locked_packages=installed,
        )
        await rattler.install(
            records,
            prefix,
            installed_packages=installed,
            show_progress=False,
            # py-rattler passes this to the FFI unchanged, which wants the
            # inner object rather than the wrapper.
            requested_specs=[ms._match_spec for ms in match_specs],
        )

    asyncio.run(run())
