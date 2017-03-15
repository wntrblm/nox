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
import nox.sessions
import nox.virtualenv

import pytest


def test__normalize_path():
    envdir = 'envdir'
    assert nox.sessions._normalize_path(envdir, u'hello') == 'envdir/hello'
    assert nox.sessions._normalize_path(envdir, b'hello') == 'envdir/hello'
    assert nox.sessions._normalize_path(
        envdir, 'hello(world)') == 'envdir/hello-world'
    assert nox.sessions._normalize_path(
        envdir, 'hello(world, meep)') == 'envdir/hello-world-meep'
    assert nox.sessions._normalize_path(
        envdir, 'tests(interpreter="python2.7", django="1.10")') == (
        'envdir/tests-interpreter-python2-7-django-1-10')


def test__normalize_path_hash():
    envdir = 'd' * (100 - len('bin/pythonX.Y') - 10)
    norm_path = nox.sessions._normalize_path(
        envdir, 'a-really-long-virtualenv-path')
    assert 'a-really-long-virtualenv-path' not in norm_path
    assert len(norm_path) < 100


def test__normalize_path_give_up():
    envdir = 'd' * 100
    norm_path = nox.sessions._normalize_path(
        envdir, 'any-path')
    assert 'any-path' in norm_path


@pytest.fixture
def make_one_config():
    def factory(*args, **kwargs):
        config = nox.sessions.SessionConfig(*args, **kwargs)
        return config
    return factory


def test_config_constructor_defaults(make_one_config):
    config = make_one_config()
    assert config.interpreter is None
    assert config._commands == []
    assert config.env == {}
    assert config.posargs == []
    assert config.reuse_existing_virtualenv is False


def test_config_constructor_args(make_one_config):
    config = make_one_config([1, 2, 3])
    assert config.posargs == [1, 2, 3]


def test_config_chdir(make_one_config):
    config = make_one_config()
    config.chdir('meep')
    command = config._commands[0]
    assert command.func == os.chdir
    assert command.args == ('meep',)
    assert str(command) == 'chdir meep'


def test_config_run(make_one_config):
    def test_func():
        pass

    config = make_one_config()
    config.run('echo')
    config.run('echo', '1', '2')
    config.run('echo', '1', '2', silent=True)
    config.run(test_func, 1, 2, three=4)

    assert config._commands[0].args == ('echo',)
    assert config._commands[1].args == ('echo', '1', '2')
    assert config._commands[2].args == ('echo', '1', '2')
    assert config._commands[2].silent is True
    assert config._commands[3].func == test_func
    assert config._commands[3].args == (1, 2)
    assert config._commands[3].kwargs == {'three': 4}

    with pytest.raises(ValueError):
        config.run()


def test_config_install(make_one_config):
    config = make_one_config()
    config.install('mock')
    config.install('mock', 'pytest')
    config.install('-r', 'somefile.txt')
    config.install('-e', 'dir')

    assert config._commands[0].deps == ('mock',)
    assert config._commands[1].deps == ('mock', 'pytest')
    assert config._commands[2].deps == ('-r', 'somefile.txt')
    assert config._commands[3].deps == ('-e', 'dir')

    with pytest.raises(ValueError):
        config.install()

    with pytest.raises(ValueError):
        config.virtualenv = False
        config.install('mock')


def test_config_log(make_one_config):
    config = make_one_config()
    config.log('test', '1', '2')


def test_config_error(make_one_config):
    config = make_one_config()
    with pytest.raises(nox.sessions._SessionQuit):
        config.error('test', '1', '2')


@pytest.fixture
def make_one():
    def factory(*args, **kwargs):
        session = nox.sessions.Session(*args, **kwargs)
        return session
    return factory


class MockConfig(object):
    def __init__(self, **kwargs):
        self.__dict__['noxfile'] = './nox.py'
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


def test__create_config_auto_chdir(make_one):
    def session_func(sess):
        pass
    global_config = MockConfig(posargs=[1, 2, 3], noxfile='/path/to/nox.py')
    session = make_one('test', 'sig', session_func, global_config)
    session._create_config()
    assert len(session.config._commands) == 1
    assert isinstance(session.config._commands[0], nox.command.ChdirCommand)
    assert session.config._commands[0].path == '/path/to'


class MockVenv(object):
    def __init__(self, path, interpreter, reuse_existing=False):
        self.path = path
        self.interpreter = interpreter
        self.reuse_existing = reuse_existing
        self.install_called = False

    def create(self):
        return not self.reuse_existing

    def install(self):
        self.install_called = True


@pytest.fixture
def venv_session(make_one):
    global_config = MockConfig(
        envdir='envdir',
        reuse_existing_virtualenvs=False)
    session = make_one('test', 'sig', mock.Mock(), global_config)
    session.config = MockConfig(
        interpreter='interpreter',
        reuse_existing_virtualenv=False,
        virtualenv=True)

    with mock.patch('nox.sessions.VirtualEnv', MockVenv):
        yield global_config, session


def test__create_venv(venv_session):
    global_config, session = venv_session

    session._create_venv()
    assert session.venv.path == os.path.join('envdir', 'sig')
    assert session.venv.interpreter == 'interpreter'
    assert session.venv.reuse_existing is False
    assert session._should_install_deps is True


def test__create_venv_global_reuse(venv_session):
    global_config, session = venv_session
    global_config.reuse_existing_virtualenvs = True
    session._create_venv()
    assert session.venv.path == os.path.join('envdir', 'sig')
    assert session.venv.interpreter == 'interpreter'
    assert session.venv.reuse_existing is True
    assert session._should_install_deps is False


def test__create_venv_local_reuse(venv_session):
    global_config, session = venv_session
    global_config.reuse_existing_virtualenvs = False
    session.config.reuse_existing_virtualenv = True
    session._create_venv()
    assert session.venv.path == os.path.join('envdir', 'sig')
    assert session.venv.interpreter == 'interpreter'
    assert session.venv.reuse_existing is True


def test__create_venv_virtualenv_false(venv_session):
    global_config, session = venv_session
    session.config.virtualenv = False
    session._create_venv()
    assert isinstance(session.venv, nox.virtualenv.ProcessEnv)
    assert not session._should_install_deps


def test__run_commands(make_one):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())

    cmd1 = mock.Mock(spec=nox.command.Command)
    cmd2 = mock.Mock(spec=nox.command.FunctionCommand)

    session.config = MockConfig(
        _commands=[cmd1, cmd2],
        env={'SIGIL2': '345'})
    session.venv = mock.Mock()
    session.venv.env = {'SIGIL': '123'}
    session.venv.bin = '/venv/bin'

    session._run_commands()

    assert cmd1.called
    assert cmd1.call_args[1]['env_override'] == {
        'SIGIL': '123', 'SIGIL2': '345'}
    assert cmd1.call_args[1]['path_override'] == session.venv.bin
    assert cmd2.called


def test_execute(make_one):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())

    session.config = MockConfig()
    session._create_config = mock.Mock()
    session._create_venv = mock.Mock()
    session._run_commands = mock.Mock()

    assert session.execute()

    assert session._create_config.called
    assert session._create_venv.called
    assert session._run_commands.called


def test_execute_install(make_one):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())
    session.venv = mock.Mock()
    commands = [
        nox.command.InstallCommand(['-r', 'requirements.txt'])
    ]
    session.config = MockConfig(_commands=commands, env={})

    session._run_commands()

    session.venv.install.assert_called_with('-r', 'requirements.txt')


def test_execute_install_skip(make_one):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())
    session.venv = mock.Mock()
    commands = [
        nox.command.InstallCommand(['-r', 'requirements.txt'])
    ]
    session.config = MockConfig(_commands=commands, env={})
    session._should_install_deps = False

    session._run_commands()

    assert not session.venv.install.called


def test_execute_chdir(make_one, tmpdir):
    tmpdir.join('dir2').ensure(dir=True)

    session = make_one('test', 'sig', mock.Mock(), MockConfig())
    session.venv = mock.Mock()
    session.venv.env = {}

    current_cwd = os.getcwd()
    observed_cwds = []

    def observe_cwd():
        observed_cwds.append(os.getcwd())

    commands = [
        nox.command.FunctionCommand(os.chdir, [tmpdir.strpath]),
        nox.command.FunctionCommand(observe_cwd),
        nox.command.FunctionCommand(os.chdir, [tmpdir.join('dir2').strpath]),
        nox.command.FunctionCommand(observe_cwd),
    ]

    session.config = MockConfig(_commands=commands, env={})
    session._create_config = mock.Mock()
    session._create_venv = mock.Mock()

    assert session.execute()

    assert observed_cwds == [
        tmpdir.strpath,
        tmpdir.join('dir2').strpath]

    assert os.getcwd() == current_cwd


def test_execute_error(make_one, tmpdir):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())

    def mock_run_commands():
        raise nox.command.CommandFailed('test')

    session.config = MockConfig(_dir='.')
    session._create_config = mock.Mock()
    session._create_venv = mock.Mock()
    session._run_commands = mock_run_commands

    assert not session.execute()


def test_execute_interrupted(make_one, tmpdir):
    session = make_one('test', 'sig', mock.Mock(), MockConfig())

    def mock_run_commands():
        raise KeyboardInterrupt()

    session.config = MockConfig(_dir='.')
    session._create_config = mock.Mock()
    session._create_venv = mock.Mock()
    session._run_commands = mock_run_commands

    with pytest.raises(KeyboardInterrupt):
        session.execute()


def test_execute_session_quit(make_one):
    def bad_config(session):
        session.error('meep')

    session = make_one('test', 'sig', bad_config, MockConfig(posargs=[]))

    assert not session.execute()
