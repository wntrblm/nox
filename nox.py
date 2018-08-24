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


@nox.session(python=["3.5", "3.6", "3.7"])
def tests(session):
    session.install("-r", "requirements-test.txt")
    session.install("-e", ".[tox_to_nox]")
    tests = session.posargs or ["tests/"]
    session.run(
        "py.test", "--cov=nox", "--cov-config", ".coveragerc", "--cov-report=", *tests
    )
    session.notify("cover")


@nox.session
def cover(session):
    session.install("coverage")
    if ON_APPVEYOR:
        fail_under = "--fail-under=99"
    else:
        fail_under = "--fail-under=100"
    session.run("coverage", "report", fail_under, "--show-missing")
    session.run("coverage", "erase")


@nox.session(python="3.6")
def blacken(session):
    session.install("black")
    session.run("black", "nox", "tests", "nox.py", "setup.py")


@nox.session(python="3.6")
def lint(session):
    session.install("flake8", "flake8-import-order", "black")
    session.run("black", "--check", "nox", "tests", "nox.py", "setup.py")
    session.run("flake8", "nox", "tests")


@nox.session(python="3.6")
def docs(session):
    session.run("rm", "-rf", "docs/_build")
    session.install("-r", "requirements-test.txt")
    session.install(".")
    session.cd("docs")
    session.run(
        "sphinx-build", "-b", "html", "-W", "-d", "_build/doctrees", ".", "_build/html"
    )
