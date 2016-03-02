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

import sys

import mock

import nox.command

import pytest

PYTHON = sys.executable


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
    command = make_one([PYTHON, '-c', 'print(123)'])

    result = command.run()

    assert result is True


def test_run_silent(make_one, capsys):
    command = make_one([PYTHON, '-c', 'print(123)'], silent=True)

    result = command.run()
    out, _ = capsys.readouterr()

    assert '123' in result
    assert out == ''


def test_run_env(make_one):
    command = make_one(
        [PYTHON, '-c', 'import os; print(os.environ["SIGIL"])'],
        silent=True, env={'SIGIL': '123'})

    result = command.run()

    assert '123' in result


def test_run_not_found(make_one):
    command = make_one(['nonexistentcmd'])

    with pytest.raises(nox.command.CommandFailed):
        command.run()


def test_run_path_nonexistent(make_one):
    command = make_one(
        [PYTHON, '-c', 'import sys; print(sys.executable)'],
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

    with mock.patch('nox.command.popen') as mock_command:
        mock_command.return_value = (0, '')
        command.run()
        mock_command.assert_called_with(
            [executable.strpath], env=None, silent=True)


def test_exit_codes(make_one):
    command_exit_code_0 = make_one(
        [PYTHON, '-c', 'import sys; sys.exit(0)'])
    command_exit_code_1 = make_one(
        [PYTHON, '-c', 'import sys; sys.exit(1)'])

    assert command_exit_code_0.run()

    with pytest.raises(nox.command.CommandFailed):
        command_exit_code_1.run()

    command_exit_code_1.success_codes = [1, 2]
    assert command_exit_code_1.run()


def test_fail_with_silent(make_one, capsys):
    command = make_one(
        [PYTHON, '-c',
         'import sys; sys.stdout.write("out");'
         'sys.stderr.write("err"); sys.exit(1)'],
        silent=True)

    with pytest.raises(nox.command.CommandFailed):
        command.run()
        out, err = capsys.readouterr()
        assert 'out' in err
        assert 'err' in err


def test_interrupt(make_one):
    command = make_one('echo', '123')

    mock_proc = mock.Mock()
    mock_proc.communicate.side_effect = KeyboardInterrupt()

    with mock.patch('subprocess.Popen', return_value=mock_proc):
        with pytest.raises(nox.command.CommandFailed):
            command.run()


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
