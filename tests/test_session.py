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

import nox.command
import nox.session

import pytest


@pytest.fixture
def make_one_config():
    def factory(*args, **kwargs):
        config = nox.session.SessionConfig(*args, **kwargs)
        return config
    return factory


def test_config_constructor_defaults(make_one_config):
    config = make_one_config()
    assert config.interpreter is None
    assert config._dependencies == []
    assert config._commands == []
    assert config.env == {}
    assert config._dir == '.'
    assert config.posargs == []
    assert config.reuse_existing_virtualenv is False


def test_config_constructor_args(make_one_config):
    config = make_one_config([1, 2, 3])
    assert config.posargs == [1, 2, 3]


def test_config_chdir(make_one_config):
    config = make_one_config()
    config.chdir('meep')
    assert config._dir == 'meep'


def test_config_run(make_one_config):
    def test_func():
        pass

    config = make_one_config()
    config.run('echo')
    config.run('echo', '1', '2')
    config.run('echo', '1', '2', silent=True)
    config.run(test_func)

    assert config._commands[0].args == ('echo',)
    assert config._commands[1].args == ('echo', '1', '2')
    assert config._commands[2].args == ('echo', '1', '2')
    assert config._commands[2].silent is True
    assert config._commands[3].func == test_func

    with pytest.raises(ValueError):
        config.run()

    with pytest.raises(ValueError):
        config.run(test_func, 1)


def test_config_install(make_one_config):
    config = make_one_config()
    config.install('mock')
    config.install('mock', 'pytest')
    config.install('-r', 'somefile.txt')
    config.install('-e', 'dir')

    assert config._dependencies[0] == ('mock',)
    assert config._dependencies[1] == ('mock', 'pytest')
    assert config._dependencies[2] == ('-r', 'somefile.txt')
    assert config._dependencies[3] == ('-e', 'dir')

    with pytest.raises(ValueError):
        config.install()


@pytest.fixture
def make_one():
    def factory(*args, **kwargs):
        session = nox.session.Session(*args, **kwargs)
        return session
    return factory


class MockConfig(object):
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)


def test_constructor(make_one):
    def mock_func():
        pass

    global_config = MockConfig()
    session = make_one('test', 'sig', mock_func, global_config)

    assert session.name == 'test'
    assert session.signature == 'sig'
    assert session.func == mock_func
    assert session.global_config == global_config


def test__create_config(make_one):
    mock_func = mock.Mock()
    global_config = MockConfig(posargs=[1, 2, 3])
    session = make_one('test', 'sig', mock_func, global_config)

    session._create_config()

    mock_func.assert_called_with(session.config)
    assert session.config.posargs == [1, 2, 3]


def test__create_venv(make_one):
    global_config = MockConfig(
        envdir='envdir',
        reuse_existing_virtualenvs=False)
    session = make_one('test', 'sig', mock.Mock(), global_config)

    with mock.patch('nox.session.VirtualEnv') as venv_mock:
        session.config = MockConfig(
            interpreter='interpreter',
            reuse_existing_virtualenv=False)
        session._create_venv()
        venv_mock.assert_called_with(
            os.path.join('envdir', 'test'),
            interpreter='interpreter',
            reuse_existing=False)

        # Global re-use
        global_config.reuse_existing_virtualenvs = True
        session._create_venv()
        venv_mock.assert_called_with(
            os.path.join('envdir', 'test'),
            interpreter='interpreter',
            reuse_existing=True)

        # Local re-use
        global_config.reuse_existing_virtualenvs = False
        session.config.reuse_existing_virtualenv = True
        session._create_venv()
        venv_mock.assert_called_with(
            os.path.join('envdir', 'test'),
            interpreter='interpreter',
            reuse_existing=True)


def test__install_dependencies(make_one):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())

    session.config = MockConfig(_dependencies=[
        ('pytest',),
        ('-r', 'somefile.txt'),
        ('-e', 'somepath')
    ])

    session.venv = mock.Mock()

    session._install_dependencies()

    session.venv.install.assert_has_calls([
        mock.call('pytest'),
        mock.call('-r', 'somefile.txt'),
        mock.call('-e', 'somepath')
    ])


class MockCommand(nox.command.Command):
    def __init__(self):
        self.path = None
        self.env = None
        self.called = False

    def __call__(self):
        self.called = True


class MockFunctionCommand(nox.command.FunctionCommand):
    def __init__(self):
        self.called = False

    def __call__(self):
        self.called = True


def test__run_commands(make_one):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())

    cmd1 = MockCommand()
    cmd2 = MockFunctionCommand()

    session.config = MockConfig(
        _commands=[cmd1, cmd2],
        env={'SIGIL2': '345'})
    session.venv = mock.Mock()
    session.venv.env = {'SIGIL': '123'}
    session.venv.bin = '/venv/bin'

    session._run_commands()

    assert cmd1.called
    assert cmd2.called


def test_execute(make_one):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())

    session.config = MockConfig(_dir='.')
    session._create_config = mock.Mock()
    session._create_venv = mock.Mock()
    session._install_dependencies = mock.Mock()
    session._run_commands = mock.Mock()

    assert session.execute()

    assert session._create_config.called
    assert session._create_venv.called
    assert session._install_dependencies.called
    assert session._run_commands.called


def test_execute_chdir(make_one, tmpdir):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())

    def mock_run_commands():
        assert os.getcwd() == tmpdir.strpath

    session.config = MockConfig(_dir=tmpdir.strpath)
    session._create_config = mock.Mock()
    session._create_venv = mock.Mock()
    session._install_dependencies = mock.Mock()
    session._run_commands = mock_run_commands

    assert session.execute()


def test_execute_error(make_one, tmpdir):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())

    def mock_run_commands():
        raise nox.command.CommandFailed('test')

    session.config = MockConfig(_dir='.')
    session._create_config = mock.Mock()
    session._create_venv = mock.Mock()
    session._install_dependencies = mock.Mock()
    session._run_commands = mock_run_commands

    assert not session.execute()
