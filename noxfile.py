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

import os

import nox


ON_APPVEYOR = os.environ.get("APPVEYOR") == "True"


nox.options.sessions = ["cover"]
# nox.options.stop_on_first_error = True


@nox.session(python=["3.5", "3.6", "3.7"])
def tests(session):
    """Run test suite with pytest."""
    session.install("-r", "requirements-test.txt")
    session.install("-e", ".[tox_to_nox]")
    tests = session.posargs or ["tests/"]
    session.run(
        "pytest", "--cov=nox", "--cov-config", ".coveragerc", "--cov-report=", *tests
    )
    session.notify("cover")


@nox.session
def cover(session):
    """Coverage analysis."""
    session.install("coverage")
    if ON_APPVEYOR:
        fail_under = "--fail-under=99"
    else:
        fail_under = "--fail-under=100"
    session.run("coverage", "report", fail_under, "--show-missing")
    session.run("coverage", "erase")


@nox.session(python="3.6")
def blacken(session):
    """Run black code formater."""
    session.install("black")
    session.run("black", "nox", "tests", "noxfile.py", "setup.py")


@nox.session(python="3.6")
def lint(session):
    """Lint using flake8."""
    session.install("flake8", "flake8-import-order", "black")
    session.run("black", "--check", "nox", "tests", "noxfile.py", "setup.py")
    session.run("flake8", "nox", "tests")


@nox.session(python="3.6")
def docs(session):
    """Build the documentation."""
    session.run("rm", "-rf", "docs/_build", external=True)
    session.install("-r", "requirements-test.txt")
    session.install(".")
    session.cd("docs")
    sphinx_args = ["-b", "html", "-W", "-d", "_build/doctrees", ".", "_build/html"]

    if "serve" not in session.posargs:
        sphinx_cmd = "sphinx-build"
    else:
        sphinx_cmd = "sphinx-autobuild"
        sphinx_args.insert(0, "--open-browser")

    session.run(sphinx_cmd, *sphinx_args)
