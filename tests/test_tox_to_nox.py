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

import sys
import textwrap

import pytest
from nox import tox_to_nox


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
            """
    [tox]
    envlist = py27
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            """
    import nox


    @nox.session(python='python2.7')
    def py27(session):
        session.install('.')
    """
        ).lstrip()
    )


def test_skipinstall(makeconfig):
    result = makeconfig(
        textwrap.dedent(
            """
    [tox]
    envlist = py27

    [testenv]
    skip_install = True
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            """
    import nox


    @nox.session(python='python2.7')
    def py27(session):
    """
        ).lstrip()
    )


def test_usedevelop(makeconfig):
    result = makeconfig(
        textwrap.dedent(
            """
    [tox]
    envlist = py27

    [testenv]
    usedevelop = True
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            """
    import nox


    @nox.session(python='python2.7')
    def py27(session):
        session.install('-e', '.')
    """
        ).lstrip()
    )


def test_commands(makeconfig):
    result = makeconfig(
        textwrap.dedent(
            """
    [tox]
    envlist = lint

    [testenv:lint]
    basepython = python2.7
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
            """
    import nox


    @nox.session(python='python2.7')
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
            """
    [tox]
    envlist = lint

    [testenv:lint]
    basepython = python2.7
    deps =
      flake8
      gcp-devrel-py-tools>=0.0.3
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            """
    import nox


    @nox.session(python='python2.7')
    def lint(session):
        session.install('flake8', 'gcp-devrel-py-tools>=0.0.3')
        session.install('.')
    """
        ).lstrip()
    )


def test_env(makeconfig):
    result = makeconfig(
        textwrap.dedent(
            """
    [tox]
    envlist = lint

    [testenv:lint]
    basepython = python2.7
    setenv =
        SPHINX_APIDOC_OPTIONS=members,inherited-members,show-inheritance
        TEST=meep
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            """
    import nox


    @nox.session(python='python2.7')
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
            """
    [tox]
    envlist = lint

    [testenv:lint]
    basepython = python2.7
    changedir = docs
    """
        )
    )

    assert (
        result
        == textwrap.dedent(
            """
    import nox


    @nox.session(python='python2.7')
    def lint(session):
        session.install('.')
        session.chdir('docs')
    """
        ).lstrip()
    )
