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

import collections
import os
import sys

import contexter
import mock
import pkg_resources
import pytest

import nox
import nox.main
import nox.registry
import nox.sessions


RESOURCES = os.path.join(os.path.dirname(__file__), 'resources')
VERSION = pkg_resources.get_distribution('nox-automation').version


class Namespace(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_global_config_constructor():
    args = Namespace(
        noxfile='noxfile',
        envdir='dir',
        sessions=['1', '2'],
        keywords='red and blue',
        list_sessions=False,
        reuse_existing_virtualenvs=True,
        stop_on_first_error=False,
        posargs=['a', 'b', 'c'],
        report=None)

    config = nox.main.GlobalConfig(args)

    assert config.noxfile == 'noxfile'
    assert config.envdir == os.path.abspath('dir')
    assert config.sessions == ['1', '2']
    assert config.keywords == 'red and blue'
    assert config.list_sessions is False
    assert config.reuse_existing_virtualenvs is True
    assert config.stop_on_first_error is False
    assert config.posargs == ['a', 'b', 'c']

    args.posargs = ['--', 'a', 'b', 'c']
    config = nox.main.GlobalConfig(args)
    assert config.posargs == ['a', 'b', 'c']


def test_load_user_nox_module():
    noxfile_path = os.path.join(RESOURCES, 'noxfile.py')
    noxfile_module = nox.main.load_user_nox_module(noxfile_path)

    assert noxfile_module.SIGIL == '123'


def test_discover_session_functions_naming_convention():
    def session_1():
        pass

    def session_2():
        pass

    def notasession():
        pass

    mock_module = Namespace(
        __name__='irrelevant',
        session_1=session_1,
        session_2=session_2,
        notasession=notasession)

    session_functions = nox.main.discover_session_functions(mock_module)

    assert session_functions == collections.OrderedDict((
        ('1', session_1),
        ('2', session_2),
    ))


def test_discover_session_functions_decorator():
    @nox.session
    def foo():
        pass

    @nox.session
    def bar():
        pass

    def notasession():
        pass

    mock_module = Namespace(
        __name__=foo.__module__,
        foo=foo,
        bar=bar,
        notasession=notasession,
    )
    session_functions = nox.main.discover_session_functions(mock_module)

    assert session_functions == collections.OrderedDict((
        ('foo', foo),
        ('bar', bar),
    ))


def test_discover_session_functions_mix():
    @nox.session
    def foo():
        pass

    def session_bar():
        pass

    def notasession():
        pass

    mock_module = Namespace(
        __name__=foo.__module__,
        foo=foo,
        session_bar=session_bar,
        notasession=notasession,
    )
    session_functions = nox.main.discover_session_functions(mock_module)

    assert session_functions == collections.OrderedDict((
        ('foo', foo),
        ('bar', session_bar),
    ))


def test_run(monkeypatch, capsys, tmpdir):

    class MockSession(nox.sessions.Session):
        def __init__(self, name='session_name', signature=None,
                     global_config=None, return_value=True):
            super(MockSession, self).__init__(
                name, signature, None, global_config)
            self.execute = mock.Mock()
            self.execute.return_value = return_value

    global_config = Namespace(
        noxfile='somefile.py',
        sessions=None,
        keywords=None,
        list_sessions=False,
        stop_on_first_error=False,
        posargs=[],
        report=None,)
    user_nox_module = mock.Mock()
    session_functions = {'foo': mock.Mock(), 'bar': mock.Mock()}
    sessions = [
        MockSession(),
        MockSession()
    ]

    with contexter.ExitStack() as stack:
        mock_load_user_module = stack.enter_context(mock.patch(
            'nox.main.load_user_nox_module',
            side_effect=lambda _: user_nox_module))
        mock_discover_session_functions = stack.enter_context(mock.patch(
            'nox.main.discover_session_functions',
            side_effect=lambda _: session_functions))
        mock_make_session = stack.enter_context(mock.patch(
            'nox.manifest.Manifest.make_session', side_effect=[sessions]))

        # Default options
        result = nox.main.run(global_config)
        assert result

        # The `load_user_module` function receives an absolute path,
        # but it should end with the noxfile argument.
        mock_load_user_module.assert_called_once()
        _, args, _ = mock_load_user_module.mock_calls[0]
        assert args[0].endswith('somefile.py')

        mock_discover_session_functions.assert_called_with(user_nox_module)
        calls = mock_make_session.call_args_list
        assert len(calls) == 2
        assert calls[0][0] == ('foo', session_functions['foo'])
        assert calls[1][0] == ('bar', session_functions['bar'])

        for session in sessions:
            assert session.execute.called
            session.execute.reset_mock()

        # List sessions
        global_config.list_sessions = True
        result = nox.main.run(global_config)
        assert result

        out, _ = capsys.readouterr()
        assert '* session_name' in out

        global_config.list_sessions = False

        # One failing session at the beginning, should still execute all.
        failing_session = MockSession(return_value=False)
        sessions.insert(0, failing_session)

        result = nox.main.run(global_config)
        assert not result

        for session in sessions:
            assert session.execute.called
            session.execute.reset_mock()

        # Now it should stop after the first failed session.
        global_config.stop_on_first_error = True

        result = nox.main.run(global_config)
        assert not result

        assert sessions[0].execute.called is True
        assert sessions[1].execute.called is False
        assert sessions[2].execute.called is False

        for session in sessions:
            session.execute.reset_mock()

        sessions[0].execute.return_value = True

        # Add a skipped session
        skipped_session = MockSession(
            return_value=nox.sessions.SessionStatus.SKIP)
        sessions.insert(0, skipped_session)

        result = nox.main.run(global_config)
        assert result

        assert sessions[0].execute.called is True
        assert sessions[1].execute.called is True
        assert sessions[2].execute.called is True

        for session in sessions:
            session.execute.reset_mock()

        # This time it should only run a subset of sessions
        sessions[0].name = '1'
        sessions[1].name = '2'
        sessions[2].name = '3'

        global_config.sessions = ['1', '3']

        result = nox.main.run(global_config)
        assert result

        assert sessions[0].execute.called is True
        assert sessions[1].execute.called is False
        assert sessions[2].execute.called is True

        for session in sessions:
            session.execute.reset_mock()

        # Try to run with a session that doesn't exist.
        global_config.sessions = ['1', 'doesntexist']

        result = nox.main.run(global_config)
        assert not result

        assert sessions[0].execute.called is False
        assert sessions[1].execute.called is False
        assert sessions[2].execute.called is False

        for session in sessions:
            session.execute.reset_mock()

        # Now we'll try with parametrized sessions. Calling the basename
        # should execute all parametrized versions.
        sessions[0].name = 'a'
        sessions[0].signature = 'a(1)'
        sessions[1].name = 'a'
        sessions[1].signature = 'a(2)'
        sessions[2].name = 'b'

        global_config.sessions = ['a']

        result = nox.main.run(global_config)
        assert result

        assert sessions[0].execute.called is True
        assert sessions[1].execute.called is True
        assert sessions[2].execute.called is False

        for session in sessions:
            session.execute.reset_mock()

        # Calling the signature of should only call one parametrized version.
        global_config.sessions = ['a(2)']

        result = nox.main.run(global_config)
        assert result

        assert sessions[0].execute.called is False
        assert sessions[1].execute.called is True
        assert sessions[2].execute.called is False

        for session in sessions:
            session.execute.reset_mock()

        # Calling a signature that does not exist should not call any version.
        global_config.sessions = ['a(1)', 'a(3)', 'b']

        result = nox.main.run(global_config)
        assert not result

        assert sessions[0].execute.called is False
        assert sessions[1].execute.called is False
        assert sessions[2].execute.called is False

        # Calling a name of an empty parametrized session should work.
        sessions[:] = [nox.sessions.Session(
            'name', None, nox.main._null_session_func, global_config)]
        global_config.sessions = ['name']

        assert nox.main.run(global_config)

        # Using -k should filter sessions
        sessions[:] = [
            MockSession('red', 'red()'),
            MockSession('blue', 'blue()'),
            MockSession('red', 'red(blue)'),
            MockSession('redder', 'redder()')]
        global_config.sessions = None
        global_config.keywords = 'red and not blue'

        assert nox.main.run(global_config)
        assert sessions[0].execute.called
        assert not sessions[1].execute.called
        assert not sessions[2].execute.called
        assert sessions[3].execute.called

        global_config.keywords = None

        # Reporting should work
        report = tmpdir.join('report.json')
        global_config.report = str(report)
        assert nox.main.run(global_config)
        assert report.exists()

        global_config.report = None

        # Summary should fail if there's an invalid status
        sessions[0].execute.return_value = 2990
        global_config.sessions = [sessions[0].name]
        with pytest.raises(ValueError):
            nox.main.run(global_config)


def test_run_file_not_found():
    global_config = Namespace(
        noxfile='somefile.py')
    result = nox.main.run(global_config)
    assert not result


def test_main():
    # No args
    sys.argv = [sys.executable]
    with mock.patch('nox.main.run') as run_mock:
        nox.main.main()
        assert run_mock.called
        config = run_mock.call_args[0][0]
        assert config.noxfile == 'nox.py'
        assert config.envdir.endswith('.nox')
        assert config.sessions is None
        assert config.reuse_existing_virtualenvs is False
        assert config.stop_on_first_error is False
        assert config.posargs == []

    # Long-form args
    sys.argv = [
        sys.executable,
        '--noxfile', 'noxfile.py',
        '--envdir', '.other',
        '--sessions', '1', '2',
        '--reuse-existing-virtualenvs',
        '--stop-on-first-error']
    with mock.patch('nox.main.run') as run_mock:
        nox.main.main()
        assert run_mock.called
        config = run_mock.call_args[0][0]
        assert config.noxfile == 'noxfile.py'
        assert config.envdir.endswith('.other')
        assert config.sessions == ['1', '2']
        assert config.reuse_existing_virtualenvs is True
        assert config.stop_on_first_error is True
        assert config.posargs == []

    # Short-form args
    sys.argv = [
        sys.executable,
        '-f', 'noxfile.py',
        '-s', '1', '2',
        '-r']
    with mock.patch('nox.main.run') as run_mock:
        nox.main.main()
        assert run_mock.called
        config = run_mock.call_args[0][0]
        assert config.noxfile == 'noxfile.py'
        assert config.sessions == ['1', '2']
        assert config.reuse_existing_virtualenvs is True

    sys.argv = [
        sys.executable,
        '-e', '1', '2']
    with mock.patch('nox.main.run') as run_mock:
        nox.main.main()
        assert run_mock.called
        config = run_mock.call_args[0][0]
        assert config.sessions == ['1', '2']

    # Posargs
    sys.argv = [
        sys.executable,
        '1', '2', '3']
    with mock.patch('nox.main.run') as run_mock:
        nox.main.main()
        assert run_mock.called
        config = run_mock.call_args[0][0]
        assert config.posargs == ['1', '2', '3']

    sys.argv = [
        sys.executable,
        '--', '1', '2', '3']
    with mock.patch('nox.main.run') as run_mock:
        nox.main.main()
        assert run_mock.called
        config = run_mock.call_args[0][0]
        assert config.posargs == ['1', '2', '3']

    sys.argv = [
        sys.executable,
        '--', '1', '2', '3', '-f', '--baz']
    with mock.patch('nox.main.run') as run_mock:
        nox.main.main()
        assert run_mock.called
        config = run_mock.call_args[0][0]
        assert config.posargs == ['1', '2', '3', '-f', '--baz']


def test_main_version(capsys):
    sys.argv = [sys.executable, '--version']

    with contexter.ExitStack() as stack:
        run_mock = stack.enter_context(mock.patch('nox.main.run'))
        exit_mock = stack.enter_context(mock.patch('sys.exit'))
        nox.main.main()
        _, err = capsys.readouterr()
        assert VERSION in err
        exit_mock.assert_not_called()
        run_mock.assert_not_called()


def test_main_failure():
    sys.argv = [sys.executable]

    with contexter.ExitStack() as stack:
        run_mock = stack.enter_context(mock.patch('nox.main.run'))
        exit_mock = stack.enter_context(mock.patch('sys.exit'))
        run_mock.return_value = False
        nox.main.main()
        exit_mock.assert_called_with(1)


def test_main_interrupted():
    sys.argv = [sys.executable]

    with contexter.ExitStack() as stack:
        run_mock = stack.enter_context(mock.patch('nox.main.run'))
        exit_mock = stack.enter_context(mock.patch('sys.exit'))
        run_mock.side_effect = KeyboardInterrupt()
        nox.main.main()
        exit_mock.assert_called_with(1)
