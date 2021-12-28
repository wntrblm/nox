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


import functools
import os
import platform
import shutil
import sys

import nox

ON_WINDOWS_CI = "CI" in os.environ and platform.system() == "Windows"

# Skip 'conda_tests' if user doesn't have conda installed
nox.options.sessions = ["tests", "cover", "lint", "docs"]
if shutil.which("conda"):
    nox.options.sessions.append("conda_tests")


def is_python_version(session, version):
    if not version.startswith(session.python):
        return False
    py_version = session.run("python", "-V", silent=True)
    py_version = py_version.partition(" ")[2].strip()
    return py_version.startswith(version)


@nox.session(python=["3.6", "3.7", "3.8", "3.9", "3.10"])
def tests(session):
    """Run test suite with pytest."""
    session.create_tmp()
    session.install("-r", "requirements-test.txt")
    session.install("-e", ".[tox_to_nox]")
    tests = session.posargs or ["tests/"]
    if is_python_version(session, "3.6.0"):
        session.run("pytest", *tests)
        return
    session.run(
        "pytest",
        "--cov=nox",
        "--cov-config",
        "pyproject.toml",
        "--cov-report=",
        *tests,
        env={"COVERAGE_FILE": f".coverage.{session.python}"},
    )
    session.notify("cover")


@nox.session(python=["3.6", "3.7", "3.8", "3.9", "3.10"], venv_backend="conda")
def conda_tests(session):
    """Run test suite with pytest."""
    session.create_tmp()
    session.conda_install(
        "--file", "requirements-conda-test.txt", "--channel", "conda-forge"
    )
    session.install("-e", ".", "--no-deps")
    tests = session.posargs or ["tests/"]
    session.run("pytest", *tests)


@nox.session
def cover(session):
    """Coverage analysis."""
    if ON_WINDOWS_CI:
        return

    # 3.10 produces different coverage results for some reason
    # see https://github.com/theacodes/nox/issues/478
    fail_under = 100
    py_version = sys.version_info
    if py_version.major == 3 and py_version.minor == 10:
        fail_under = 99

    session.install("coverage[toml]")
    session.run("coverage", "combine")
    session.run("coverage", "report", f"--fail-under={fail_under}", "--show-missing")
    session.run("coverage", "erase")


@nox.session(python="3.9")
def lint(session: nox.Session):
    """Run pre-commit linting."""
    session.install("pre-commit")
    # See https://github.com/theacodes/nox/issues/545
    # and https://github.com/pre-commit/pre-commit/issues/2178#issuecomment-1002163763
    session.run(
        "pre-commit",
        "run",
        "--all-files",
        "--show-diff-on-failure",
        env={"SETUPTOOLS_USE_DISTUTILS": "stdlib"},
    )


@nox.session
def docs(session):
    """Build the documentation."""
    output_dir = os.path.join(session.create_tmp(), "output")
    doctrees, html = map(
        functools.partial(os.path.join, output_dir), ["doctrees", "html"]
    )
    shutil.rmtree(output_dir, ignore_errors=True)
    session.install("-r", "requirements-test.txt")
    session.install(".")
    session.cd("docs")
    sphinx_args = ["-b", "html", "-W", "-d", doctrees, ".", html]

    if not session.interactive:
        sphinx_cmd = "sphinx-build"
    else:
        sphinx_cmd = "sphinx-autobuild"
        sphinx_args.insert(0, "--open-browser")

    session.run(sphinx_cmd, *sphinx_args)
