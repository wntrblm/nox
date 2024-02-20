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

import sys
import textwrap

import pytest
from tox import __version__ as TOX_VERSION

tox_to_nox = pytest.importorskip("nox.tox_to_nox")

TOX4 = TOX_VERSION[0] == "4"
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
PYTHON_VERSION_NODOT = PYTHON_VERSION.replace(".", "")


@pytest.fixture
def makeconfig(tmpdir):
    def makeconfig(toxini_content):
        tmpdir.join("tox.ini").write(toxini_content)
        old = tmpdir.chdir()
        try:
            sys.argv = [sys.executable]
            tox_to_nox.main()
            return tmpdir.join("noxfile.py").read()
        finally:
            old.chdir()

    return makeconfig


def test_trivial(makeconfig):
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


def test_skipinstall(makeconfig):
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


def test_usedevelop(makeconfig):
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


def test_commands(makeconfig):
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


def test_deps(makeconfig):
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


def test_env(makeconfig):
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


def test_chdir(makeconfig):
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


def test_dash_in_envname(makeconfig):
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


@pytest.mark.skipif(TOX4, reason="Not supported in tox 4.")
def test_non_identifier_in_envname(makeconfig, capfd):
    result = makeconfig(
        textwrap.dedent(
            f"""
            [tox]
            envlist = test-with-&

            [testenv:test-with-&]
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
        def test_with_&(session):
            session.install('.')
        """
        ).lstrip()
    )

    out, _ = capfd.readouterr()

    assert (
        out == "Environment 'test_with_&' is not a valid nox session name.\n"
        "Manually update the session name in noxfile.py before running nox.\n"
    )


def test_descriptions_into_docstrings(makeconfig):
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
