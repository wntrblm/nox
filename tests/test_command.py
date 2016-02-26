import os
import mock
import nox.command
import py
import pytest
import sys


@pytest.fixture
def make_one():
    def factory(*args, **kwargs):
        return nox.command.Command(*args, **kwargs)
    return factory


@pytest.fixture
def make_one_func():
    def factory(*args, **kwargs):
        return nox.command.FunctionCommand(*args, **kwargs)
    return factory


def test_constructor_defaults(make_one):
    command = make_one(['echo', '123'])
    assert command.args == ['echo', '123']
    assert command.silent is False
    assert command.path is None
    assert command.success_codes == [0]


def test_constructor_explicit(make_one):
    command = make_one(
        ['echo', '123'],
        silent=True,
        path='/one/two/three',
        success_codes=[1, 2, 3])
    assert command.args == ['echo', '123']
    assert command.silent is True
    assert command.path is '/one/two/three'
    assert command.success_codes == [1, 2, 3]


def test_run_defaults(make_one, capsys):
    command = make_one(['echo', '123'])

    result = command.run()
    out, _ = capsys.readouterr()

    assert result
    assert out == '123\n'


def test_run_silent(make_one, capsys):
    command = make_one(['echo', '123'], silent=True)

    result = command.run()
    out, _ = capsys.readouterr()

    assert result == '123\n'
    assert out == ''


def test_run_env(make_one):
    command = make_one(['env'], silent=True, env={'SIGIL': '123'})

    result = command.run()

    assert result == 'SIGIL=123\n'


def test_run_not_found(make_one):
    command = make_one(['nonexistentcmd'])

    with pytest.raises(nox.command.CommandFailed):
        command.run()


def test_run_path_nonexistent(make_one):
    command = make_one(
        ['python', '-c', 'import sys; print(sys.executable)'],
        silent=True,
        path='/non/existent')

    result = command.run()

    assert '/non/existent' not in result


def test_run_path_existent(make_one, tmpdir, monkeypatch):
    executable = tmpdir.join('testexc')
    executable.ensure('')
    executable.chmod(0o700)

    command = make_one(
        ['testexc'],
        silent=True,
        path=tmpdir.strpath)

    with mock.patch('sh.Command') as mock_command:
        command.run()
        mock_command.assert_called_with(executable.strpath)


def test_exit_codes(make_one):
    command_exit_code_0 = make_one(
        ['python', '-c', 'import sys; sys.exit(0)'])
    command_exit_code_1 = make_one(
        ['python', '-c', 'import sys; sys.exit(1)'])

    assert command_exit_code_0.run()

    with pytest.raises(nox.command.CommandFailed):
        command_exit_code_1.run()

    command_exit_code_1.success_codes = [1, 2]
    assert command_exit_code_1.run()


def test_fail_with_silent(make_one, capsys):
    command = make_one(
        ['python', '-c',
         'import sys; sys.stdout.write("out");'
         'sys.stderr.write("err"); sys.exit(1)'],
        silent=True)

    with pytest.raises(nox.command.CommandFailed):
        command.run()
        out, err = capsys.readouterr()
        assert 'out' in out
        assert 'err' in err


def test_function_command(make_one_func):
    mock_func = mock.MagicMock()
    mock_func.__name__ = lambda self: 'mock_func'

    command = make_one_func(mock_func)

    assert command.run()
    assert mock_func.called


def test_function_command_fail(make_one_func):
    mock_func = mock.MagicMock(side_effect=ValueError('123'))
    mock_func.__name__ = lambda self: 'mock_func'

    command = make_one_func(mock_func)

    with pytest.raises(nox.command.CommandFailed):
        command.run()
