# Copyright 2016 Jon Wayne Parrott
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

import nox


@nox.session
def default(session):
    session.install('-r', 'requirements-test.txt')
    session.install('-e', '.[tox_to_nox]')
    tests = session.posargs or ['tests/']
    session.run(
        'py.test', '--cov=nox', '--cov-config', '.coveragerc',
        '--cov-report=', *tests)
    session.notify('cover')


@nox.session
@nox.parametrize('version', ['2.7', '3.4', '3.5', '3.6'])
def interpreters(session, version):
    default(session)
    session.interpreter = 'python' + version


@nox.session
def cover(session):
    session.install('coverage')
    session.run('coverage', 'report', '--fail-under=100', '--show-missing')
    session.run('coverage', 'erase')


@nox.session
def lint(session):
    session.install('flake8', 'flake8-import-order')
    session.run(
        'flake8',
        '--import-order-style=google',
        '--application-import-names=nox,tests',
        'nox', 'tests')


@nox.session
def docs(session):
    session.interpreter = 'python3.6'
    session.run('rm', '-rf', 'docs/_build')
    session.install('-r', 'requirements-test.txt')
    # Readthedocs uses setuptools to install the package, so we do as well.
    session.run('python', 'setup.py', 'install')
    session.cd('docs')
    session.run(
        'sphinx-build',
        '-b', 'html',
        '-d', '_build/doctrees',
        '.', '_build/html')
