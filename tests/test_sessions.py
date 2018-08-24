# Copyright 2016 Alethea Katherine Flowers
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

import argparse
import logging
import os
import sys
from unittest import mock

import pytest

import nox.command
from nox.logger import logger
import nox.manifest
import nox.registry
import nox.sessions
import nox.virtualenv


def test__normalize_path():
    envdir = "envdir"
    normalize = nox.sessions._normalize_path
    assert normalize(envdir, u"hello") == os.path.join("envdir", "hello")
    assert normalize(envdir, b"hello") == os.path.join("envdir", "hello")
    assert normalize(envdir, "hello(world)") == os.path.join("envdir", "hello-world")
    assert normalize(envdir, "hello(world, meep)") == os.path.join(
        "envdir", "hello-world-meep"
    )
    assert normalize(envdir, 'tests(interpreter="python2.7", django="1.10")') == (
        os.path.join("envdir", "tests-interpreter-python2-7-django-1-10")
    )


def test__normalize_path_hash():
    envdir = "d" * (100 - len("bin/pythonX.Y") - 10)
    norm_path = nox.sessions._normalize_path(envdir, "a-really-long-virtualenv-path")
    assert "a-really-long-virtualenv-path" not in norm_path
    assert len(norm_path) < 100


def test__normalize_path_give_up():
    envdir = "d" * 100
    norm_path = nox.sessions._normalize_path(envdir, "any-path")
    assert "any-path" in norm_path


class TestSession:
    def make_session_and_runner(self):
        runner = nox.sessions.SessionRunner(
            name="test",
            signature="test",
            func=mock.sentinel.func,
            global_config=argparse.Namespace(posargs=mock.sentinel.posargs),
            manifest=mock.create_autospec(nox.manifest.Manifest),
        )
        runner.venv = mock.create_autospec(nox.virtualenv.VirtualEnv)
        runner.venv.env = {}
        return nox.sessions.Session(runner=runner), runner

    def test_properties(self):
        session, runner = self.make_session_and_runner()

        assert session.env is runner.venv.env
        assert session.posargs is runner.global_config.posargs
        assert session.virtualenv is runner.venv
        assert session.bin is runner.venv.bin

    def test_chdir(self, tmpdir):
        cdto = str(tmpdir.join("cdbby").ensure(dir=True))
        current_cwd = os.getcwd()

        session, _ = self.make_session_and_runner()

        session.chdir(cdto)

        assert os.getcwd() == cdto
        os.chdir(current_cwd)

    def test_run_bad_args(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(ValueError, match="arg"):
            session.run()

    def test_run_with_func(self):
        session, _ = self.make_session_and_runner()

        assert session.run(lambda a, b: a + b, 1, 2) == 3

    def test_run_with_func_error(self):
        session, _ = self.make_session_and_runner()

        def raise_value_error():
            raise ValueError("meep")

        with pytest.raises(nox.command.CommandFailed):
            assert session.run(raise_value_error)

    def test_run_success(self):
        session, _ = self.make_session_and_runner()
        result = session.run(sys.executable, "-c", "print(123)")
        assert result

    def test_run_error(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(nox.command.CommandFailed):
            session.run(sys.executable, "-c", "import sys; sys.exit(1)")

    def test_run_overly_env(self):
        session, runner = self.make_session_and_runner()
        runner.venv.env["A"] = "1"
        runner.venv.env["B"] = "2"
        result = session.run(
            sys.executable,
            "-c",
            'import os; print(os.environ["A"], os.environ["B"])',
            env={"B": "3"},
            silent=True,
        )
        assert result.strip() == "1 3"

    def test_install_bad_args(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(ValueError, match="arg"):
            session.install()

    def test_install_not_a_virtualenv(self):
        session, runner = self.make_session_and_runner()

        runner.venv = None

        with pytest.raises(ValueError, match="virtualenv"):
            session.install()

    def test_install(self):
        session, runner = self.make_session_and_runner()

        with mock.patch.object(session, "run", autospec=True) as run:
            session.install("requests", "urllib3")
            run.assert_called_once_with(
                "pip", "install", "--upgrade", "requests", "urllib3", silent=True
            )

    def test_notify(self):
        session, runner = self.make_session_and_runner()

        session.notify("other")

        runner.manifest.notify.assert_called_once_with("other")

    def test_log(self, caplog):
        caplog.set_level(logging.INFO)
        session, _ = self.make_session_and_runner()

        session.log("meep")

        assert "meep" in caplog.text

    def test_error(self, caplog):
        caplog.set_level(logging.ERROR)
        session, _ = self.make_session_and_runner()

        with pytest.raises(nox.sessions._SessionQuit):
            session.error("meep")

        assert "meep" in caplog.text

    def test_error_no_log(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(nox.sessions._SessionQuit):
            session.error()

    def test_skip_no_log(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(nox.sessions._SessionSkip):
            session.skip()


class TestSessionRunner:
    def make_runner(self):
        func = mock.Mock()
        func.python = None
        func.reuse_venv = False
        runner = nox.sessions.SessionRunner(
            name="test",
            signature="test(1, 2)",
            func=func,
            global_config=argparse.Namespace(
                noxfile=os.path.join(os.getcwd(), "nox.py"),
                envdir="envdir",
                posargs=mock.sentinel.posargs,
                reuse_existing_virtualenvs=False,
            ),
            manifest=mock.create_autospec(nox.manifest.Manifest),
        )
        return runner

    def test_properties(self):
        runner = self.make_runner()

        assert runner.name == "test"
        assert runner.signature == "test(1, 2)"
        assert runner.func is not None
        assert runner.global_config.posargs == mock.sentinel.posargs
        assert isinstance(runner.manifest, nox.manifest.Manifest)

    def test__create_venv_process_env(self):
        runner = self.make_runner()
        runner.func.python = False

        runner._create_venv()

        assert isinstance(runner.venv, nox.virtualenv.ProcessEnv)

    @mock.patch("nox.virtualenv.VirtualEnv.create", autospec=True)
    def test__create_venv(self, create):
        runner = self.make_runner()

        runner._create_venv()

        create.assert_called_once_with(runner.venv)
        assert isinstance(runner.venv, nox.virtualenv.VirtualEnv)
        assert runner.venv.location.endswith(os.path.join("envdir", "test-1-2"))
        assert runner.venv.interpreter is None
        assert runner.venv.reuse_existing is False

    @mock.patch("nox.virtualenv.VirtualEnv.create", autospec=True)
    def test__create_venv_options(self, create):
        runner = self.make_runner()
        runner.func.python = "coolpython"
        runner.func.reuse_venv = True

        runner._create_venv()

        create.assert_called_once_with(runner.venv)
        assert isinstance(runner.venv, nox.virtualenv.VirtualEnv)
        assert runner.venv.interpreter is "coolpython"
        assert runner.venv.reuse_existing is True

    def make_runner_with_mock_venv(self):
        runner = self.make_runner()
        runner._create_venv = mock.Mock()
        return runner

    def test_execute_noop_success(self, caplog):
        caplog.set_level(logging.DEBUG)

        runner = self.make_runner_with_mock_venv()

        result = runner.execute()

        assert result
        runner.func.assert_called_once_with(mock.ANY)
        assert "Running session test(1, 2)" in caplog.text

    def test_execute_quit(self):
        runner = self.make_runner_with_mock_venv()

        def func(session):
            session.error("meep")

        runner.func = func

        result = runner.execute()

        assert result.status == nox.sessions.Status.ABORTED

    def test_execute_skip(self):
        runner = self.make_runner_with_mock_venv()

        def func(session):
            session.skip("meep")

        runner.func = func

        result = runner.execute()

        assert result.status == nox.sessions.Status.SKIPPED

    def test_execute_failed(self):
        runner = self.make_runner_with_mock_venv()

        def func(session):
            raise nox.command.CommandFailed()

        runner.func = func

        result = runner.execute()

        assert result.status == nox.sessions.Status.FAILED

    def test_execute_interrupted(self):
        runner = self.make_runner_with_mock_venv()

        def func(session):
            raise KeyboardInterrupt()

        runner.func = func

        with pytest.raises(KeyboardInterrupt):
            runner.execute()

    def test_execute_exception(self):
        runner = self.make_runner_with_mock_venv()

        def func(session):
            raise ValueError("meep")

        runner.func = func

        result = runner.execute()

        assert result.status == nox.sessions.Status.FAILED


class TestResult:
    def test_init(self):
        result = nox.sessions.Result(
            session=mock.sentinel.SESSION, status=mock.sentinel.STATUS
        )
        assert result.session == mock.sentinel.SESSION
        assert result.status == mock.sentinel.STATUS

    def test__bool_true(self):
        for status in (nox.sessions.Status.SUCCESS, nox.sessions.Status.SKIPPED):
            result = nox.sessions.Result(session=object(), status=status)
            assert bool(result)
            assert result.__bool__()
            assert result.__nonzero__()

    def test__bool_false(self):
        for status in (nox.sessions.Status.FAILED, nox.sessions.Status.ABORTED):
            result = nox.sessions.Result(session=object(), status=status)
            assert not bool(result)
            assert not result.__bool__()
            assert not result.__nonzero__()

    def test__imperfect(self):
        result = nox.sessions.Result(object(), nox.sessions.Status.SUCCESS)
        assert result.imperfect == "was successful"
        result = nox.sessions.Result(object(), nox.sessions.Status.FAILED)
        assert result.imperfect == "failed"

    def test__log_success(self):
        result = nox.sessions.Result(object(), nox.sessions.Status.SUCCESS)
        with mock.patch.object(logger, "success") as success:
            result.log("foo")
            success.assert_called_once_with("foo")

    def test__log_warning(self):
        result = nox.sessions.Result(object(), nox.sessions.Status.SKIPPED)
        with mock.patch.object(logger, "warning") as warning:
            result.log("foo")
            warning.assert_called_once_with("foo")

    def test__log_error(self):
        result = nox.sessions.Result(object(), nox.sessions.Status.FAILED)
        with mock.patch.object(logger, "error") as error:
            result.log("foo")
            error.assert_called_once_with("foo")

    def test__serialize(self):
        result = nox.sessions.Result(
            session=argparse.Namespace(
                signature="siggy", name="namey", func=mock.Mock()
            ),
            status=nox.sessions.Status.SUCCESS,
        )
        answer = result.serialize()
        assert answer["name"] == "namey"
        assert answer["result"] == "success"
        assert answer["result_code"] == 1
        assert answer["signature"] == "siggy"
