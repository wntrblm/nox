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


def test_create_interpreter(make_one):
    venv, dir = make_one(interpreter='python3')
    venv.create()
    assert dir.join('bin', 'python').check()
    assert dir.join('bin', 'python3').check()
