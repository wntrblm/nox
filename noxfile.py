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

import nox

ON_WINDOWS_CI = "CI" in os.environ and platform.system() == "Windows"


def is_python_version(session, version):
    if not version.startswith(session.python):
        return False
    py_version = session.run("python", "-V", silent=True)
    py_version = py_version.partition(" ")[2].strip()
    return py_version.startswith(version)


@nox.session(python=["3.6", "3.7", "3.8", "3.9"])
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
        "pytest", "--cov=nox", "--cov-config", ".coveragerc", "--cov-report=", *tests
    )
    session.notify("cover")


@nox.session(python=["3.6", "3.7", "3.8", "3.9"], venv_backend="conda")
def conda_tests(session):
    """Run test suite with pytest."""
    session.create_tmp()
    session.conda_install(
        "--file", "requirements-conda-test.txt", "--channel", "conda-forge"
    )
    session.install("contexter", "--no-deps")
    session.install("-e", ".", "--no-deps")
    tests = session.posargs or ["tests/"]
    session.run("pytest", *tests)


@nox.session
def cover(session):
    """Coverage analysis."""
    if ON_WINDOWS_CI:
        return

    session.install("coverage")
    session.run("coverage", "report", "--fail-under=100", "--show-missing")
    session.run("coverage", "erase")


@nox.session(python="3.8")
def blacken(session):
    """Run black code formatter."""
    session.install("black==19.3b0", "isort==4.3.21")
    files = ["nox", "tests", "noxfile.py", "setup.py"]
    session.run("black", *files)
    session.run("isort", "--recursive", *files)


@nox.session(python="3.8")
def lint(session):
    session.install("flake8==3.7.8", "black==19.3b0", "isort==4.3.21", "mypy==0.720")
    session.run(
        "mypy",
        "--disallow-untyped-defs",
        "--warn-unused-ignores",
        "--ignore-missing-imports",
        "nox",
    )
    files = ["nox", "tests", "noxfile.py", "setup.py"]
    session.run("black", "--check", *files)
    session.run("isort", "--check", "--recursive", *files)
    session.run("flake8", "nox", *files)


@nox.session(python="3.8")
def docs(session):
    """Build the documentation."""
    output_dir = os.path.join(session.create_tmp(), "output")
    doctrees, html = map(
        functools.partial(os.path.join, output_dir), ["doctrees", "html"]
    )
    session.run("rm", "-rf", output_dir, external=True)
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
