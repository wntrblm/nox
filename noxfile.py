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


from __future__ import annotations

import contextlib
import functools
import os
import shutil
import sqlite3
import sys

import nox

ON_WINDOWS_CI = "CI" in os.environ and sys.platform.startswith("win32")

nox.needs_version = ">=2024.4.15"
nox.options.default_venv_backend = "uv|virtualenv"

PYPROJECT = nox.project.load_toml("pyproject.toml")

ALL_PYTHONS = [
    c.split()[-1]
    for c in PYPROJECT["project"]["classifiers"]
    if c.startswith("Programming Language :: Python :: 3.")
]


@nox.session(python=ALL_PYTHONS)
def tests(session: nox.Session) -> None:
    """Run test suite with pytest."""

    coverage_file = f".coverage.{sys.platform}.{session.python}"

    session.create_tmp()  # Fixes permission errors on Windows
    session.install(*PYPROJECT["dependency-groups"]["test"], "uv")
    session.install("-e.[tox_to_nox]")
    extra_env = {"PYTHONWARNDEFAULTENCODING": "1"}
    session.run(
        "pytest",
        "--cov",
        "--cov-config",
        "pyproject.toml",
        "--cov-report=",
        *session.posargs,
        env={
            "COVERAGE_FILE": coverage_file,
            **extra_env,
        },
    )

    if sys.platform.startswith("win"):
        with contextlib.closing(sqlite3.connect(coverage_file)) as con, con:
            con.execute("UPDATE file SET path = REPLACE(path, '\\', '/')")
            con.execute("DELETE FROM file WHERE SUBSTR(path, 2, 1) == ':'")


@nox.session(venv_backend="conda", default=shutil.which("conda"))
def conda_tests(session: nox.Session) -> None:
    """Run test suite set up with conda."""
    session.conda_install(
        "--file", "requirements-conda-test.txt", channel="conda-forge"
    )
    session.install("-e.", "--no-deps")
    session.run("pytest", *session.posargs)


@nox.session(venv_backend="mamba", default=shutil.which("mamba"))
def mamba_tests(session: nox.Session) -> None:
    """Run test suite set up with mamba."""
    session.conda_install(
        "--file", "requirements-conda-test.txt", channel="conda-forge"
    )
    session.install("-e.", "--no-deps")
    session.run("pytest", *session.posargs)


@nox.session(venv_backend="micromamba", default=shutil.which("micromamba"))
def micromamba_tests(session: nox.Session) -> None:
    """Run test suite set up with micromamba."""
    session.conda_install(
        "--file", "requirements-conda-test.txt", channel="conda-forge"
    )
    session.install("-e.", "--no-deps")
    session.run("pytest", *session.posargs)


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
        python_version = session.python[4:]
        implementation = "pypy"
    else:
        python_version = session.python
        implementation = "cpython"
    session.run(
        "python",
        "-c",
        "import sys; assert '.'.join(str(v) for v in sys.version_info[:2]) =="
        f" '{python_version}'",
    )
    if python_version[:2] != "2.":
        session.run(
            "python",
            "-c",
            f"import sys; assert sys.implementation.name == '{implementation}'",
        )


@nox.session(
    python=[
        *ALL_PYTHONS,
        "pypy-3.10",
    ],
    default=False,
)
def github_actions_default_tests(session: nox.Session) -> None:
    """Check default versions installed by the nox GHA Action"""
    assert sys.version_info[:2] == (3, 11)
    _check_python_version(session)


@nox.session(
    python=[
        *ALL_PYTHONS,
        "pypy3.8",
        "pypy3.9",
        "pypy3.10",
    ],
    default=False,
)
def github_actions_all_tests(session: nox.Session) -> None:
    """Check all versions installed by the nox GHA Action"""
    _check_python_version(session)
