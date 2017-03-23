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

import nox
import nox.main
import nox.registry
import nox.sessions


RESOURCES = os.path.join(os.path.dirname(__file__), 'resources')


class Namespace(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_global_config_constructor():
    args = Namespace(
        noxfile='noxfile',
        envdir='dir',
        sessions=['1', '2'],
        list_sessions=False,
        reuse_existing_virtualenvs=True,
        stop_on_first_error=False,
        posargs=['a', 'b', 'c'],
        report=None)

    config = nox.main.GlobalConfig(args)

    assert config.noxfile == 'noxfile'
    assert config.envdir == os.path.abspath('dir')
    assert config.sessions == ['1', '2']
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


def test_make_sessions():
    def session_1():
        pass

    def session_2():
        pass

    session_functions = collections.OrderedDict((
        ('1', session_1),
        ('2', session_2),
    ))
    global_config = Namespace()
    sessions = nox.main.make_sessions(session_functions, global_config)

    assert sessions[0].name == '1'
    assert sessions[0].func == session_1
    assert sessions[0].global_config == global_config
    assert sessions[1].name == '2'
    assert sessions[1].func == session_2
    assert sessions[1].global_config == global_config


def test_make_session_parametrized():

    @nox.parametrize('arg', [1, 2])
    def session_a(arg):
        pass

    @nox.parametrize('foo', [1, 2])
    @nox.parametrize('bar', [3, 4])
    def session_b():
        pass

    @nox.parametrize('unused', [])
    def session_empty():
        pass

    session_functions = collections.OrderedDict((
        ('a', session_a),
        ('b', session_b),
        ('empty', session_empty),
    ))
    global_config = Namespace()
    sessions = nox.main.make_sessions(session_functions, global_config)

    assert sessions[0].signature == 'a(arg=1)'
    assert sessions[0].name == 'a'
    assert sessions[1].signature == 'a(arg=2)'
    assert sessions[1].name == 'a'
    assert sessions[2].signature == 'b(bar=3, foo=1)'
    assert sessions[2].name == 'b'
    assert sessions[3].signature == 'b(bar=4, foo=1)'
    assert sessions[3].name == 'b'
    assert sessions[4].signature == 'b(bar=3, foo=2)'
    assert sessions[4].name == 'b'
    assert sessions[5].signature == 'b(bar=4, foo=2)'
    assert sessions[5].name == 'b'
    assert sessions[6].signature is None
    assert sessions[6].name == 'empty'


def test_run(monkeypatch, capsys, tmpdir):

    class MockSession(object):
        def __init__(self, return_value=True):
            self.name = 'session_name'
            self.signature = None
            self.execute = mock.Mock()
            self.execute.return_value = return_value

    global_config = Namespace(
        noxfile='somefile.py',
        sessions=None,
        list_sessions=False,
        stop_on_first_error=False,
        posargs=[],
        report=None)
    user_nox_module = mock.Mock()
    session_functions = mock.Mock()
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
        mock_make_sessions = stack.enter_context(mock.patch(
            'nox.main.make_sessions', side_effect=lambda _1, _2: sessions))

        # Default options
        result = nox.main.run(global_config)
        assert result

        # The `load_user_module` function receives an absolute path,
        # but it ishould end with the noxfile argument.
        mock_load_user_module.assert_called_once()
        _, args, _ = mock_load_user_module.mock_calls[0]
        assert args[0].endswith('somefile.py')

        mock_discover_session_functions.assert_called_with(user_nox_module)
        mock_make_sessions.assert_called_with(session_functions, global_config)

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

        # This time it should only run a subset of sessions
        sessions[0].execute.return_value = True
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

        # Reporting should work
        global_config.report = str(tmpdir.join('report.json'))
        assert nox.main.run(global_config)


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
