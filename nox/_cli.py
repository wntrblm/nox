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

"""The Nox `main` function and helpers."""

from __future__ import annotations

__lazy_modules__ = {
    "importlib",
    "importlib.metadata",
    "nox._options",
    "nox._version",
    "nox.command",
    "nox.logger",
    "nox.project",
    "nox.registry",
    "nox.virtualenv",
    "packaging",
    "packaging.requirements",
    "packaging.specifiers",
    "packaging.utils",
    "pathlib",
    "shutil",
    "subprocess",
    "urllib",
    "urllib.parse",
}

import importlib.metadata
import os
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NoReturn, cast

import packaging.requirements
import packaging.specifiers
import packaging.utils

import nox.command
import nox.registry
import nox.virtualenv
from nox import _options, tasks, workflow
from nox._options import DefaultStr
from nox._version import get_nox_version
from nox.logger import logger, setup_logging
from nox.project import load_toml

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterator

__all__ = ["execute_workflow", "main", "nox_main"]


def __dir__() -> list[str]:
    return __all__


def execute_workflow(args: Namespace) -> int:
    """
    Execute the appropriate tasks.
    """

    return workflow.execute(
        global_config=args,
        workflow=(
            tasks.load_nox_module,
            tasks.merge_noxfile_options,
            tasks.discover_manifest,
            tasks.filter_manifest,
            tasks.honor_list_request,
            tasks.honor_usage_request,
            tasks.run_manifest,
            tasks.print_summary,
            tasks.create_report,
            tasks.final_reduce,
        ),
    )


def get_dependencies(
    req: packaging.requirements.Requirement,
) -> Iterator[packaging.requirements.Requirement]:
    """
    Gets all dependencies. Raises ModuleNotFoundError if a package is not installed.
    """
    seen: set[tuple[packaging.utils.NormalizedName, frozenset[str]]] = set()

    def expand(
        req: packaging.requirements.Requirement,
    ) -> Iterator[packaging.requirements.Requirement]:
        # Skip the metadata read and re-expansion for requirements already
        # visited with the same extras; this avoids rescanning shared
        # dependencies reachable through multiple extras and guards against
        # dependency cycles. The requirement itself is still yielded so that
        # every specifier is checked downstream.
        key = (packaging.utils.canonicalize_name(req.name), frozenset(req.extras))
        if key in seen:
            yield req
            return
        seen.add(key)

        info = importlib.metadata.metadata(req.name)
        yield req

        dist_list = info.get_all("requires-dist") or []
        extra_list = [packaging.requirements.Requirement(mk) for mk in dist_list]
        for extra in req.extras:
            for ireq in extra_list:
                if ireq.marker and not ireq.marker.evaluate({"extra": extra}):
                    continue
                yield from expand(ireq)

    yield from expand(req)


def check_dependencies(dependencies: list[str]) -> bool:
    """
    Checks to see if a list of dependencies is currently installed.
    """
    itr_deps = (packaging.requirements.Requirement(d) for d in dependencies)
    deps = [d for d in itr_deps if not d.marker or d.marker.evaluate()]

    # Select the one nox dependency (required)
    nox_dep = [d for d in deps if packaging.utils.canonicalize_name(d.name) == "nox"]
    if not nox_dep:
        msg = "Must have a nox dependency in TOML script dependencies"
        raise ValueError(msg)

    try:
        expanded_deps = {d for req in deps for d in get_dependencies(req)}
    except ModuleNotFoundError:
        return False

    for dep in expanded_deps:
        if dep.specifier:
            version = importlib.metadata.version(dep.name)
            if not dep.specifier.contains(version):
                return False
        if dep.url:
            dist = importlib.metadata.distribution(dep.name)
            if not check_url_dependency(dep.url, dist):
                return False

    return True


def check_requires_python(requires_python: str | None, version: str) -> bool:
    """
    Checks a Python version like ``"3.12.1"`` against a ``requires-python``
    specifier set. True if no specifier is given.
    """
    if not requires_python:
        return True
    try:
        specifiers = packaging.specifiers.SpecifierSet(requires_python)
    except packaging.specifiers.InvalidSpecifier as err:
        msg = f'Invalid "requires-python": {requires_python!r} ({err})'
        raise SystemExit(msg) from err
    # prereleases=True so a prerelease interpreter still matches plain specs
    # like ">=3.9"; PEP 440 ordering (beta < final) still applies.
    return specifiers.contains(version, prereleases=True)


def _format_python_version(version_info: tuple[int, int, int, str, int]) -> str:
    major, minor, micro, releaselevel, serial = version_info
    pre = {"alpha": "a", "beta": "b", "candidate": "rc"}.get(releaselevel, "")
    return f"{major}.{minor}.{micro}{pre}{serial if pre else ''}"


def _current_python_version() -> str:
    # Built from sys.version_info rather than platform.python_version(), which
    # can produce unparsable values like "3.13.0+" on dev builds.
    return _format_python_version(sys.version_info[:5])


def _venv_python_version(venv: nox.virtualenv.ProcessEnv) -> str | None:
    """The environment's Python version as PEP 440, or None if it can't run."""
    env = {k: v for k, v in venv._get_env({}).items() if v is not None}
    python_cmd = shutil.which("python", path=env.get("PATH"))
    if python_cmd is None:
        return None
    result = subprocess.run(
        [python_cmd, "-c", "import sys; print(*sys.version_info)"],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return None
    major, minor, micro, releaselevel, serial = result.stdout.split()
    return _format_python_version(
        (int(major), int(minor), int(micro), releaselevel, int(serial))
    )


def check_url_dependency(dep_url: str, dist: importlib.metadata.Distribution) -> bool:
    """
    Check to see if a url matches an installed distribution object. Returns false if
    this is not a clear match.
    """

    # The .origin property added in Python 3.13
    origin = getattr(dist, "origin", None)
    if origin is None:
        return False

    dep_purl = urllib.parse.urlparse(dep_url)

    if hasattr(origin, "requested_revision"):
        origin_purl = urllib.parse.urlparse(f"{origin.url}@{origin.requested_revision}")
    else:
        origin_purl = urllib.parse.urlparse(origin.url)

    return dep_purl.netloc == origin_purl.netloc and dep_purl.path == origin_purl.path


def get_main_filename() -> str | None:
    main_module = sys.modules.get("__main__")
    if (
        main_module
        and (fname := getattr(main_module, "__file__", ""))
        and os.path.exists(main_filename := os.path.abspath(fname))
    ):
        return main_filename
    return None


def _make_env(
    noxenv: Path,
    *,
    reuse_existing: bool,
    venv_backend: str,
    download_python: Literal["auto", "never", "always"],
    requires_python: str | None,
) -> nox.virtualenv.ProcessEnv:
    # python-discovery takes specifier sets like ">=3.10" directly, and
    # prefers the running interpreter when it qualifies.
    venv = nox.virtualenv.get_virtualenv(
        *venv_backend.split("|"),
        download_python=download_python,
        reuse_existing=reuse_existing,
        envdir=str(noxenv),
        interpreter=requires_python,
    )
    try:
        venv.create()
    except nox.virtualenv.InterpreterNotFound as err:
        msg = f'No Python satisfies "requires-python": {requires_python!r}'
        raise SystemExit(msg) from err
    return venv


def run_script_mode(
    noxfile: str,
    envdir: Path,
    *,
    reuse: bool,
    dependencies: list[str],
    venv_backend: str,
    download_python: Literal["auto", "never", "always"],
    requires_python: str | None,
) -> NoReturn:
    envdir.mkdir(exist_ok=True)
    noxenv = envdir.joinpath("_nox_script_mode")

    venv = _make_env(
        noxenv,
        reuse_existing=reuse,
        venv_backend=venv_backend,
        download_python=download_python,
        requires_python=requires_python,
    )
    if requires_python and not venv.is_sandboxed:
        version = _current_python_version()
        if not check_requires_python(requires_python, version):
            msg = (
                f'Python {version} does not satisfy "requires-python":'
                f' {requires_python!r}, and the "none" script backend cannot'
                " switch interpreters"
            )
            raise SystemExit(msg)
    if requires_python and venv._reused and venv.is_sandboxed:
        # A reused environment may predate a requires-python change; its
        # interpreter spec is not resolved on the reuse path.
        env_version = _venv_python_version(venv)
        if env_version is None or not check_requires_python(
            requires_python, env_version
        ):
            logger.info(
                "Recreating script environment: its Python"
                f" ({env_version or 'unknown'}) does not satisfy"
                f' "requires-python": {requires_python!r}'
            )
            venv = _make_env(
                noxenv,
                reuse_existing=False,
                venv_backend=venv_backend,
                download_python=download_python,
                requires_python=requires_python,
            )
    env = {k: v for k, v in venv._get_env({}).items() if v is not None}
    env["NOX_SCRIPT_MODE"] = "none"
    if venv.venv_backend == "uv":
        cmd = [nox.virtualenv.UV, "pip", "install"]
    else:
        # On Windows, subprocess resolves the executable against the parent
        # process's PATH, not the child env's, so resolve pip explicitly.
        pip_cmd = shutil.which("pip", path=env["PATH"])
        assert pip_cmd is not None, "pip must be discoverable in the environment"
        cmd = [pip_cmd, "install"]
    subprocess.run([*cmd, *dependencies], env=env, check=True)
    nox_cmd = shutil.which("nox", path=env["PATH"])
    assert nox_cmd is not None, "Nox must be discoverable when installed"
    args = [nox_cmd, "-f", noxfile, *sys.argv[1:]]
    # The os.exec functions don't work properly on Windows
    if sys.platform.startswith("win"):
        raise SystemExit(
            subprocess.run(
                args,
                env=env,
                stdout=None,
                stderr=None,
                encoding="utf-8",
                text=True,
                check=False,
            ).returncode
        )
    os.execle(nox_cmd, *args, env)  # pragma: nocover # noqa: S606


def main() -> None:
    _main(main_ep=False)


def nox_main() -> None:
    _main(main_ep=True)


def _main(*, main_ep: bool) -> None:
    args = _options.options.parse_args()

    if args.help:
        _options.options.print_help()
        return

    if args.version:
        print(get_nox_version(), file=sys.stderr)
        return

    setup_logging(
        color=args.color, verbose=args.verbose, add_timestamp=args.add_timestamp
    )
    nox_script_mode = os.environ.get("NOX_SCRIPT_MODE", "") or args.script_mode
    if nox_script_mode not in {"none", "reuse", "fresh"}:
        msg = f"Invalid NOX_SCRIPT_MODE: {nox_script_mode!r}, must be one of 'none', 'reuse', or 'fresh'"
        raise SystemExit(msg)
    if nox_script_mode != "none":
        noxfile = (
            args.noxfile
            if main_ep or not isinstance(args.noxfile, DefaultStr)
            else (get_main_filename() or args.noxfile)
        )
        toml_config = load_toml(os.path.expandvars(noxfile), missing_ok=True)
        dependencies = toml_config.get("dependencies")
        requires_python = toml_config.get("requires-python")
        if dependencies is None and requires_python is not None:
            # The script environment always needs nox itself to re-exec.
            dependencies = ["nox"]
        if dependencies is not None:
            # requires-python first: it raises on an invalid specifier, so it
            # must not be short-circuited away by a failing dependency check.
            valid_env = check_requires_python(
                requires_python, _current_python_version()
            ) and check_dependencies(dependencies)
            # Coverage misses this, but it's covered via subprocess call
            if not valid_env:  # pragma: nocover
                venv_backend = (
                    os.environ.get("NOX_SCRIPT_VENV_BACKEND")
                    or args.script_venv_backend
                    or (
                        toml_config.get("tool", {})
                        .get("nox", {})
                        .get("script-venv-backend", "uv|virtualenv")
                    )
                )

                download_python = (
                    os.environ.get("NOX_SCRIPT_DOWNLOAD_PYTHON")
                    or (
                        toml_config.get("tool", {})
                        .get("nox", {})
                        .get("script-download-python")
                    )
                    or args.download_python
                    or "auto"
                )

                if download_python not in ("auto", "never", "always"):
                    logger.warning(
                        f"Invalid parameter for {download_python=}. Defaulting to 'auto'"
                    )
                    download_python = "auto"
                download_python = cast(
                    "Literal['auto', 'never', 'always']", download_python
                )

                envdir = Path(args.envdir or ".nox")
                run_script_mode(
                    noxfile,
                    envdir,
                    reuse=nox_script_mode == "reuse",
                    dependencies=dependencies,
                    venv_backend=venv_backend,
                    download_python=download_python,
                    requires_python=requires_python,
                )

    nox.registry.reset()
    exit_code = execute_workflow(args)

    # Done; exit.
    sys.exit(exit_code)
