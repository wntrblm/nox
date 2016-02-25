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

import os
import mock
import nox.virtualenv
import py.test


@py.test.fixture
def make_one(tmpdir):
    def factory(*args, **kwargs):
        location = tmpdir.join('venv')
        venv = nox.virtualenv.VirtualEnv(location.strpath, *args, **kwargs)
        return (venv, location)
    return factory


def test_constructor_defaults(make_one):
    venv, _ = make_one()
    assert venv.location
    assert venv.interpreter is None
    assert venv.reuse_existing is False


def test_constructor_explicit(make_one):
    venv, _ = make_one(
        interpreter='python3.5',
        reuse_existing=True)
    assert venv.location
    assert venv.interpreter is 'python3.5'
    assert venv.reuse_existing is True


def test__setup_env(monkeypatch, make_one):
    venv, _ = make_one()
    monkeypatch.setenv('SIGIL', '123')
    venv._setup_env()
    assert venv.env['SIGIL'] == '123'
    assert venv.bin in venv.env['PATH']
    assert venv.bin not in os.environ['PATH']


def test__clean_location(monkeypatch, make_one):
    venv, dir = make_one()

    # Don't re-use existing, but doesn't currently exist.
    # Should return True indicating that the venv needs to be created.
    monkeypatch.delattr(nox.virtualenv.shutil, 'rmtree')
    assert not dir.check()
    assert venv._clean_location()

    # Re-use existing, and currently exists.
    # Should return False indicating that the venv doesn't need to be created.
    dir.mkdir()
    assert dir.check()
    venv.reuse_existing = True
    assert not venv._clean_location()

    # Don't re-use existing, and currently exists.
    # Should return True indicating the venv needs to be created.
    monkeypatch.undo()
    assert dir.check()
    venv.reuse_existing = False
    assert venv._clean_location()
    assert not dir.check()

    # Re-use existing, but doesn't exist.
    # Should return True indicating the venv needs to be created.
    venv.reuse_existing = True
    assert venv._clean_location()


def test_bin(make_one):
    venv, dir = make_one()
    assert dir.join('bin').strpath == venv.bin


def test_create(make_one):
    venv, dir = make_one()
    venv.create()
    assert dir.join('bin', 'python').check()
    assert dir.join('bin', 'pip').check()
    assert dir.join('lib').check()

    # Test running create on an existing environment. It should be deleted.
    dir.ensure('test.txt')
    venv.create()
    assert not dir.join('test.txt').check()

    # Test running create on an existing environment with reuse_exising
    # enabled, it should not be deleted.
    dir.ensure('test.txt')
    assert dir.join('test.txt').check()
    venv.reuse_existing = True
    venv.create()
    assert dir.join('test.txt').check()


def test_create_interpreter(make_one):
    venv, dir = make_one(interpreter='python3')
    venv.create()
    assert dir.join('bin', 'python').check()
    assert dir.join('bin', 'python3').check()


def test_run(monkeypatch, make_one):
    venv, _ = make_one(interpreter='python3')
    venv.env['SIGIL'] = '123'

    def mock_run(self):
        assert self.args == ['test', 'command']
        assert self.silent is True
        assert self.path == venv.bin
        assert self.env['SIGIL'] == '123'
        return 'okay :)'

    monkeypatch.setattr(nox.virtualenv.Command, 'run', mock_run)
    assert venv.run(['test', 'command']) == 'okay :)'

    def mock_run_outside_venv(self):
        assert self.args == ['test', 'command']
        assert self.silent is True
        assert self.path != venv.bin
        assert self.env is None
        return 'okay :)'

    monkeypatch.setattr(nox.virtualenv.Command, 'run', mock_run_outside_venv)
    assert venv.run(['test', 'command'], in_venv=False) == 'okay :)'


def test_install(monkeypatch, make_one):
    monkeypatch.setattr(
        nox.virtualenv.VirtualEnv, 'install_package', lambda self, _: _)
    monkeypatch.delattr(
        nox.virtualenv.VirtualEnv, 'install_requirements_file')
    venv, _ = make_one()

    venv.install('pytest')
    venv.install('pytest==1.2.3')
    venv.install('pytest>=1')
    venv.install('pytest>=1,<=5')

    with py.test.raises(AttributeError):
        venv.install('requirements.txt')

    with py.test.raises(AttributeError):
        venv.install('blah.txt')

    monkeypatch.undo()
    monkeypatch.setattr(
        nox.virtualenv.VirtualEnv,
        'install_requirements_file',
        lambda self, _: _)
    monkeypatch.delattr(
        nox.virtualenv.VirtualEnv, 'install_package')
    venv, _ = make_one()

    venv.install('requirements.txt')
    venv.install('blah.txt')

    with py.test.raises(AttributeError):
        venv.install('pytest')


def test_install_package(monkeypatch, make_one):
    monkeypatch.setattr(nox.virtualenv.VirtualEnv, 'run', mock.Mock())
    venv, _ = make_one()

    venv.install_package('pytest')
    venv.run.assert_called_with(
        ['pip', 'install', '--upgrade', 'pytest'])

    venv.install_package('pytest>=1.2.3')
    venv.run.assert_called_with(
        ['pip', 'install', '--upgrade', 'pytest>=1.2.3'])


def test_install_requirements_file(monkeypatch, make_one):
    monkeypatch.setattr(nox.virtualenv.VirtualEnv, 'run', mock.Mock())
    venv, _ = make_one()

    venv.install_requirements_file('requirements.txt')
    venv.run.assert_called_with(
        ['pip', 'install', '--upgrade', '-r', 'requirements.txt'])

    venv.install_requirements_file('blah.txt')
    venv.run.assert_called_with(
        ['pip', 'install', '--upgrade', '-r', 'blah.txt'])
