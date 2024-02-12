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

import functools
import os
import platform
import shutil
import sys
from typing import Any

import nox
import nox.command
from nox.logger import logger
from nox.sessions import SessionRunner
from nox.virtualenv import CondaEnv

ON_WINDOWS_CI = "CI" in os.environ and platform.system() == "Windows"

# Skip 'conda_tests' if user doesn't have conda installed
nox.options.sessions = ["tests", "cover", "lint", "docs"]
if shutil.which("conda"):
    nox.options.sessions.append("conda_tests")


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12"])
def tests(session: nox.Session) -> None:
    """Run test suite with pytest."""
    session.create_tmp()  # Fixes permission errors on Windows
    session.install("-r", "requirements-test.txt")
    session.install("-e", ".[tox_to_nox]")
    session.run(
        "pytest",
        "--cov=nox",
        "--cov-config",
        "pyproject.toml",
        "--cov-report=",
        *session.posargs,
        env={"COVERAGE_FILE": f".coverage.{session.python}"},
    )
    session.notify("cover")


# NOTE: moved tests to custom backend section below


@nox.session
def cover(session: nox.Session) -> None:
    """Coverage analysis."""
    if ON_WINDOWS_CI:
        return

    session.install("coverage[toml]")
    session.run("coverage", "combine")
    session.run("coverage", "report", "--fail-under=100", "--show-missing")
    session.run("coverage", "erase")


@nox.session(python="3.9")
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


@nox.session
def docs(session: nox.Session) -> None:
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
        "3.7",
        "3.8",
        "3.9",
        "3.10",
        "3.11",
        "3.12",
        "pypy3.7",
        "pypy3.8",
        "pypy3.9",
    ]
)
def github_actions_default_tests(session: nox.Session) -> None:
    """Check default versions installed by the nox GHA Action"""
    assert sys.version_info[:2] == (3, 11)
    _check_python_version(session)


# The following sessions are only to be run in CI to check the nox GHA action
@nox.session(
    python=[
        "3.7",
        "3.8",
        "3.9",
        "3.10",
        "3.11",
        "3.12",
        "pypy3.7",
        "pypy3.8",
        "pypy3.9",
    ]
)
def github_actions_all_tests(session: nox.Session) -> None:
    """Check all versions installed by the nox GHA Action"""
    _check_python_version(session)


################################################################################
# testing custom backend
################################################################################
def factory_conda_env(backend: str):
    """Create a callable backend with specified conda backend."""
    # Override CondaEnv backend
    CondaEnv.allowed_globals = ("conda", "mamba", "micromamba", "conda-lock")  # type: ignore[assignment]

    if backend not in CondaEnv.allowed_globals:
        msg = f"{backend=} must be in {CondaEnv.allowed_globals}"
        raise ValueError(msg)

    def create_conda_env(
        location: str,
        interpreter: str | None,
        reuse_existing: bool,
        venv_params: Any,
        runner: SessionRunner,
    ) -> CondaEnv:
        """
        Custom venv_backend to create conda environment from `environment.yaml` file

        This particular callable infers the file from the interpreter.  For example,
        if `interpreter = "3.8"`, then the environment file will be `environment/py3.8-conda-test.yaml`
        """
        if not interpreter:
            raise ValueError("must supply interpreter for this backend")

        venv = CondaEnv(
            location=location,
            interpreter=interpreter,
            reuse_existing=reuse_existing,
            venv_params=venv_params,
            conda_cmd=backend,
        )

        env_file = f"environment/py{interpreter}-conda-test.yaml"

        assert os.path.exists(env_file)
        # Custom creating (based on CondaEnv.create)
        if not venv._clean_location():
            logger.debug(f"Re-using existing conda env at {venv.location_name}.")
            venv._reused = True

        else:
            cmd = (
                [venv.conda_cmd]
                + (["--yes"] if venv.conda_cmd == "micromamba" else ["env"])
                + ["create", "--prefix", venv.location, "-f", env_file]
            )
            # cmd = ["conda", "env", "create", "--prefix", venv.location, "-f", env_file]

            logger.info(
                f"Creating conda env in {venv.location_name} with env file {env_file}"
            )
            logger.info(f"{cmd}")
            nox.command.run(cmd, silent=False, log=nox.options.verbose or False)

        return venv

    return create_conda_env


@nox.session(
    python=["3.7", "3.8", "3.9", "3.10"], venv_backend=factory_conda_env("conda")
)
def conda_tests(session: nox.Session) -> None:
    """Run test suite with pytest."""
    session.create_tmp()  # Fixes permission errors on Windows
    session.install("-e", ".", "--no-deps")
    session.run("pytest", *session.posargs)


@nox.session(
    python=["3.7", "3.8", "3.9", "3.10"], venv_backend=factory_conda_env("micromamba")
)
def micromamba_tests(session: nox.Session) -> None:
    """Run test suite with pytest."""
    session.create_tmp()  # Fixes permission errors on Windows
    session.install("-e", ".", "--no-deps")
    session.run("pytest", *session.posargs)


# conda lock backend
def create_conda_lock_env(
    location: str,
    interpreter: str | None,
    reuse_existing: bool,
    venv_params: Any,
    runner: SessionRunner,
) -> CondaEnv:
    if not interpreter:
        raise ValueError("must supply interpreter for this backend")

    lock_file = f"./environment/py{interpreter}-conda-test-conda-lock.yml"
    assert os.path.exists(lock_file)

    venv = CondaEnv(
        location=location,
        interpreter=interpreter,
        reuse_existing=reuse_existing,
        venv_params=venv_params,
    )

    # Custom creating (based on CondaEnv.create)
    if not venv._clean_location():
        logger.debug(f"Re-using existing conda env at {venv.location_name}.")
        venv._reused = True

    else:
        cmd = ["conda-lock", "install", "--prefix", venv.location, lock_file]

        logger.info(
            f"Creating conda env in {venv.location_name} with conda-lock {lock_file}"
        )
        nox.command.run(cmd, silent=False, log=nox.options.verbose or False)

    return venv


@nox.session(
    python=["3.11"],
    venv_backend=create_conda_lock_env,
)
def conda_lock_tests(session: nox.Session) -> None:
    session.create_tmp()
    session.install("-e", ".", "--no-deps")

    session.run("pytest", *session.posargs)


@nox.session
def bootstrap_conda_lock_tests(session: nox.Session) -> None:
    """Avoids need for conda-lock in requirements

    Instead of needing conda-lock in base environment:

        $ pipx install conda-lock
        $ nox -s conda-lock-backed ....

    You can just run:

        $ nox -s bootstrap-conda-lock
    """
    session.install("conda-lock")
    session.install("-e", ".")

    session.run("nox", "-s", "conda_lock_tests", *session.posargs)
