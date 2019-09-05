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
    """Run test suite with pytest."""
    session.install("-r", "requirements-test.txt")
    session.install("-e", ".[tox_to_nox]")
    tests = session.posargs or ["tests/"]
    session.run(
        "pytest", "--cov=nox", "--cov-config", ".coveragerc", "--cov-report=", *tests
    )
    session.notify("cover")


@nox.session(python=["3.5", "3.6", "3.7"], venv_backend="conda")
def conda_tests(session):
    """Run test suite with pytest."""
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
    session.install("coverage")
    if ON_APPVEYOR:
        fail_under = "--fail-under=99"
    else:
        fail_under = "--fail-under=100"
    session.run("coverage", "report", fail_under, "--show-missing")
    session.run("coverage", "erase")


@nox.session(python="3.7")
def blacken(session):
    """Run black code formater."""
    session.install("black==19.3b0", "isort==4.3.21")
    files = ["nox", "tests", "noxfile.py", "setup.py"]
    session.run("black", *files)
    session.run("isort", "--recursive", *files)


@nox.session(python="3.7")
def lint(session):
    session.install("flake8==3.7.8", "black==19.3b0", "mypy==0.720")
    session.run("mypy", "nox")
    files = ["nox", "tests", "noxfile.py", "setup.py"]
    session.run("black", "--check", *files)
    session.run("flake8", "nox", *files)


@nox.session(python="3.7")
def docs(session):
    """Build the documentation."""
    session.run("rm", "-rf", "docs/_build", external=True)
    session.install("-r", "requirements-test.txt")
    session.install(".")
    session.cd("docs")
    sphinx_args = ["-b", "html", "-W", "-d", "_build/doctrees", ".", "_build/html"]

    if not session.interactive:
        sphinx_cmd = "sphinx-build"
    else:
        sphinx_cmd = "sphinx-autobuild"
        sphinx_args.insert(0, "--open-browser")

    session.run(sphinx_cmd, *sphinx_args)
