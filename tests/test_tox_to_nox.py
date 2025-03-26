# Copyright 2017 Alethea Katherine Flowers
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

import os
import shutil
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# Jinja2 might be missing
tox_to_nox = pytest.importorskip("nox.tox_to_nox")

if TYPE_CHECKING:
    from collections.abc import Callable


pytestmark = pytest.mark.skipif(shutil.which("tox") is None, reason="Tox not available")

PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
PYTHON_VERSION_NODOT = PYTHON_VERSION.replace(".", "")


@pytest.fixture
def makeconfig(tmp_path: Path) -> Callable[[str], str]:
    def makeconfig(toxini_content: str) -> str:
        tmp_path.joinpath("tox.ini").write_text(toxini_content, encoding="utf-8")
        old = Path.cwd().resolve()
        os.chdir(tmp_path)
        try:
            sys.argv = [sys.executable]
            tox_to_nox.main()
            return tmp_path.joinpath("noxfile.py").read_text(encoding="utf-8")
        finally:
            os.chdir(old)

    return makeconfig


def test_trivial(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent(
            f"""
    [tox]
    envlist = py{PYTHON_VERSION_NODOT}
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            f"""
    import nox


    @nox.session(python='python{PYTHON_VERSION}')
    def py{PYTHON_VERSION_NODOT}(session):
        session.install('.')
    """
        ).lstrip()
    )


def test_skipinstall(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent(
            f"""
    [tox]
    envlist = py{PYTHON_VERSION_NODOT}

    [testenv]
    skip_install = True
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            f"""
    import nox


    @nox.session(python='python{PYTHON_VERSION}')
    def py{PYTHON_VERSION_NODOT}(session):
    """
        ).lstrip()
    )


def test_usedevelop(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent(
            f"""
    [tox]
    envlist = py{PYTHON_VERSION_NODOT}

    [testenv]
    usedevelop = True
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            f"""
    import nox


    @nox.session(python='python{PYTHON_VERSION}')
    def py{PYTHON_VERSION_NODOT}(session):
        session.install('-e', '.')
    """
        ).lstrip()
    )


def test_commands(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent(
            f"""
    [tox]
    envlist = lint

    [testenv:lint]
    basepython = python{PYTHON_VERSION}
    commands =
        python setup.py check --metadata --restructuredtext --strict
        flake8 \\
            --import-order-style=google \\
            google tests
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            f"""
    import nox


    @nox.session(python='python{PYTHON_VERSION}')
    def lint(session):
        session.install('.')
        session.run('python', 'setup.py', 'check', '--metadata', \
'--restructuredtext', '--strict')
        session.run('flake8', '--import-order-style=google', 'google', 'tests')
    """
        ).lstrip()
    )


def test_deps(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent(
            f"""
    [tox]
    envlist = lint

    [testenv:lint]
    basepython = python{PYTHON_VERSION}
    deps =
      flake8
      gcp-devrel-py-tools>=0.0.3
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            f"""
    import nox


    @nox.session(python='python{PYTHON_VERSION}')
    def lint(session):
        session.install('flake8', 'gcp-devrel-py-tools>=0.0.3')
        session.install('.')
    """
        ).lstrip()
    )


def test_env(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent(
            f"""
    [tox]
    envlist = lint

    [testenv:lint]
    basepython = python{PYTHON_VERSION}
    setenv =
        SPHINX_APIDOC_OPTIONS=members,inherited-members,show-inheritance
        TEST=meep
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            f"""
    import nox


    @nox.session(python='python{PYTHON_VERSION}')
    def lint(session):
        session.env['SPHINX_APIDOC_OPTIONS'] = \
'members,inherited-members,show-inheritance'
        session.env['TEST'] = 'meep'
        session.install('.')
    """
        ).lstrip()
    )


def test_chdir(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent(
            f"""
    [tox]
    envlist = lint

    [testenv:lint]
    basepython = python{PYTHON_VERSION}
    changedir = docs
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            f"""
    import nox


    @nox.session(python='python{PYTHON_VERSION}')
    def lint(session):
        session.install('.')
        session.chdir('docs')
    """
        ).lstrip()
    )


def test_dash_in_envname(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent(
            f"""
            [tox]
            envlist = test-with-dash

            [testenv:test-with-dash]
            basepython = python{PYTHON_VERSION}
            """
        )
    )

    assert (
        result
        == textwrap.dedent(
            f"""
        import nox


        @nox.session(python='python{PYTHON_VERSION}')
        def test_with_dash(session):
            session.install('.')
        """
        ).lstrip()
    )


def test_descriptions_into_docstrings(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent(
            f"""
            [tox]
            envlist = lint

            [testenv:lint]
            basepython = python{PYTHON_VERSION}
            description =
                runs the lint action
                now with an unnecessary second line
            """
        )
    )

    assert (
        result
        == textwrap.dedent(
            f"""
            import nox


            @nox.session(python='python{PYTHON_VERSION}')
            def lint(session):
                \"\"\"runs the lint action now with an unnecessary second line\"\"\"
                session.install('.')
            """
        ).lstrip()
    )


def test_commands_with_requirements(makeconfig: Callable[[str], str]) -> None:
    result = makeconfig(
        textwrap.dedent("""
        [tox]
        envlist = aiohttp

        [testenv]
        use_develop = true
        deps =
            pytest
            pytest-cov
            aiohttp: -r requirements/aiohttp.txt
    """)
    )

    assert (
        result
        == textwrap.dedent(f"""
    import nox


    @nox.session(python='python{PYTHON_VERSION}')
    def aiohttp(session):
        session.install('pytest', 'pytest-cov', '-r', 'requirements/aiohttp.txt')
        session.install('-e', '.')
    """).lstrip()
    )
