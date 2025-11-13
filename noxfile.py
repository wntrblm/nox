#!/usr/bin/env -S uv run --script

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

# /// script
# dependencies = ["nox>=2025.02.09"]
# ///


from __future__ import annotations

import functools
import os
import shutil
import sys

import nox

ON_WINDOWS_CI = "CI" in os.environ and sys.platform.startswith("win32")

nox.needs_version = ">=2025.02.09"
nox.options.default_venv_backend = "uv|virtualenv"

PYPROJECT = nox.project.load_toml("pyproject.toml")
ALL_PYTHONS = nox.project.python_versions(PYPROJECT)


@nox.session(python=ALL_PYTHONS)
def tests(session: nox.Session) -> None:
    """Run test suite with pytest."""

    coverage_file = f".coverage.pypi.{sys.platform}.{session.python}"
    env = {
        "PYTHONWARNDEFAULTENCODING": "1",
        "COVERAGE_FILE": coverage_file,
    }

    session.create_tmp()  # Fixes permission errors on Windows
    session.install(*PYPROJECT["dependency-groups"]["test"], "uv")
    session.install("-e.[tox_to_nox,pbs]")
    session.run("coverage", "erase", env=env)
    session.run(
        "coverage",
        "run",
        "-m",
        "pytest",
        "--numprocesses=auto",
        "-m",
        "not conda",
        *session.posargs,
        env=env,
    )
    session.run("coverage", "combine", env=env)
    session.run("coverage", "report", env=env)

    # if sys.platform.startswith("win"):
    #    with contextlib.closing(sqlite3.connect(coverage_file)) as con, con:
    #        con.execute("UPDATE file SET path = REPLACE(path, '\\', '/')")
    #        con.execute("DELETE FROM file WHERE SUBSTR(path, 2, 1) == ':'")


@nox.session(venv_backend="uv", default=False)
def minimums(session: nox.Session) -> None:
    """Run test suite with the lowest supported versions of everything. Requires uv."""
    session.create_tmp()

    session.install("-e.", "--group=test", "--resolution=lowest-direct")
    session.run("uv", "pip", "list")
    session.run("pytest", *session.posargs)


def xonda_tests(session: nox.Session, xonda: str) -> None:
    """Run test suite set up with conda/mamba/etc."""

    coverage_file = f".coverage.{xonda}.{sys.platform}.{session.python}"
    env = {"COVERAGE_FILE": coverage_file}

    session.conda_install(
        "--file", "requirements-conda-test.txt", channel="conda-forge"
    )
    session.install("-e.", "--no-deps")
    # Currently, this doesn't work on Windows either with or without quoting
    if not sys.platform.startswith("win32"):
        session.conda_install("requests<99")

    session.run("coverage", "erase", env=env)
    session.run(
        "coverage",
        "run",
        "-m",
        "pytest",
        "-m",
        "conda",
        *session.posargs,
        env=env,
    )
    session.run("coverage", "combine", env=env)
    session.run("coverage", "report", env=env)


@nox.session(venv_backend="conda", default=bool(shutil.which("conda")))
def conda_tests(session: nox.Session) -> None:
    """Run test suite set up with conda."""
    xonda_tests(session, "conda")


@nox.session(venv_backend="mamba", default=shutil.which("mamba"))
def mamba_tests(session: nox.Session) -> None:
    """Run test suite set up with mamba."""
    xonda_tests(session, "mamba")


@nox.session(venv_backend="micromamba", default=shutil.which("micromamba"))
def micromamba_tests(session: nox.Session) -> None:
    """Run test suite set up with micromamba."""
    xonda_tests(session, "micromamba")


@nox.session(default=False)
def cover(session: nox.Session) -> None:
    """Coverage analysis."""
    if ON_WINDOWS_CI:
        return

    session.install("coverage[toml]>=7.3")
    session.run("coverage", "combine")
    session.run("coverage", "report", "--fail-under=100", "--show-missing")
    session.run("coverage", "erase")


@nox.session(python="3.12")
def lint(session: nox.Session) -> None:
    """Run pre-commit linting."""
    session.install("pre-commit")
    session.run(
        "pre-commit",
        "run",
        "--all-files",
        "--show-diff-on-failure",
        "--hook-stage=manual",
        *session.posargs,
    )


@nox.session(default=False)
def docs(session: nox.Session) -> None:
    """Build the documentation."""
    output_dir = os.path.join(session.create_tmp(), "output")
    doctrees, html = map(
        functools.partial(os.path.join, output_dir), ["doctrees", "html"]
    )
    shutil.rmtree(output_dir, ignore_errors=True)
    session.install(*PYPROJECT["dependency-groups"]["docs"])
    session.install("-e.")
    session.cd("docs")
    sphinx_args = ["-b", "html", "-W", "-d", doctrees, ".", html]

    if not session.interactive:
        sphinx_cmd = "sphinx-build"
    else:
        sphinx_cmd = "sphinx-autobuild"
        sphinx_args.insert(0, "--open-browser")

    session.run(sphinx_cmd, *sphinx_args)


# The following sessions are only to be run in CI to check the nox GHA action
def _check_python_version(session: nox.Session) -> None:
    if session.python.startswith("pypy"):
        # Drop starting "pypy" and maybe "-"
        python_version = session.python.lstrip("py-")
        implementation = "pypy"
    else:
        # TODO: check free threaded match
        python_version = session.python.rstrip("t")
        implementation = "cpython"
    session.run(
        "python",
        "-c",
        "import sys; assert '.'.join(str(v) for v in sys.version_info[:2]) =="
        f" '{python_version}'",
    )
    session.run(
        "python",
        "-c",
        f"import sys; assert sys.implementation.name == '{implementation}'",
    )


@nox.session(
    python=[
        *ALL_PYTHONS,
        "pypy-3.11",
        "3.13t",
        "3.14t",
    ],
    default=False,
)
def github_actions_default_tests(session: nox.Session) -> None:
    """Check default versions installed by the nox GHA Action"""
    assert sys.version_info[:2] == (3, 12)
    _check_python_version(session)


@nox.session(
    python=[
        *ALL_PYTHONS,
        "pypy3.9",
        "pypy3.10",
        "pypy3.11",
    ],
    default=False,
)
def github_actions_all_tests(session: nox.Session) -> None:
    """Check all versions installed by the nox GHA Action"""
    _check_python_version(session)


if __name__ == "__main__":
    nox.main()
