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
import operator
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import nox.command
import nox.manifest
import nox.registry
import nox.sessions
import nox.virtualenv
import pytest
from nox import _options
from nox.logger import logger


def test__normalize_path():
    envdir = "envdir"
    normalize = nox.sessions._normalize_path
    assert normalize(envdir, "hello") == os.path.join("envdir", "hello")
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
        func = mock.Mock(spec=["python"], python="3.7")
        runner = nox.sessions.SessionRunner(
            name="test",
            signatures=["test"],
            func=func,
            global_config=_options.options.namespace(
                posargs=mock.sentinel.posargs,
                error_on_external_run=False,
                install_only=False,
            ),
            manifest=mock.create_autospec(nox.manifest.Manifest),
        )
        runner.venv = mock.create_autospec(nox.virtualenv.VirtualEnv)
        runner.venv.env = {}
        runner.venv.bin_paths = ["/no/bin/for/you"]
        return nox.sessions.Session(runner=runner), runner

    def test_create_tmp(self):
        session, runner = self.make_session_and_runner()
        with tempfile.TemporaryDirectory() as root:
            runner.global_config.envdir = root
            tmpdir = session.create_tmp()
            assert session.env["TMPDIR"] == tmpdir
            assert tmpdir.startswith(root)

    def test_create_tmp_twice(self):
        session, runner = self.make_session_and_runner()
        with tempfile.TemporaryDirectory() as root:
            runner.global_config.envdir = root
            runner.venv.bin = bin
            session.create_tmp()
            tmpdir = session.create_tmp()
            assert session.env["TMPDIR"] == tmpdir
            assert tmpdir.startswith(root)

    def test_properties(self):
        session, runner = self.make_session_and_runner()

        assert session.name is runner.friendly_name
        assert session.env is runner.venv.env
        assert session.posargs is runner.global_config.posargs
        assert session.virtualenv is runner.venv
        assert session.bin_paths is runner.venv.bin_paths
        assert session.bin is runner.venv.bin_paths[0]
        assert session.python is runner.func.python

    def test_no_bin_paths(self):
        session, runner = self.make_session_and_runner()

        runner.venv.bin_paths = None
        with pytest.raises(
            ValueError, match=r"^The environment does not have a bin directory\.$"
        ):
            session.bin
        assert session.bin_paths is None

    def test_virtualenv_as_none(self):
        session, runner = self.make_session_and_runner()

        runner.venv = None

        with pytest.raises(ValueError, match="virtualenv"):
            _ = session.virtualenv

    def test_interactive(self):
        session, runner = self.make_session_and_runner()

        with mock.patch("nox.sessions.sys.stdin.isatty") as m_isatty:
            m_isatty.return_value = True

            assert session.interactive is True

            m_isatty.return_value = False

            assert session.interactive is False

    def test_explicit_non_interactive(self):
        session, runner = self.make_session_and_runner()

        with mock.patch("nox.sessions.sys.stdin.isatty") as m_isatty:
            m_isatty.return_value = True
            runner.global_config.non_interactive = True

            assert session.interactive is False

    def test_chdir(self, tmpdir):
        cdto = str(tmpdir.join("cdbby").ensure(dir=True))
        current_cwd = os.getcwd()

        session, _ = self.make_session_and_runner()

        session.chdir(cdto)

        assert os.getcwd() == cdto
        os.chdir(current_cwd)

    def test_chdir_pathlib(self, tmpdir):
        cdto = str(tmpdir.join("cdbby").ensure(dir=True))
        current_cwd = os.getcwd()

        session, _ = self.make_session_and_runner()

        session.chdir(Path(cdto))

        assert os.getcwd() == cdto
        os.chdir(current_cwd)

    def test_run_bad_args(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(ValueError, match="arg"):
            session.run()

    def test_run_with_func(self):
        session, _ = self.make_session_and_runner()

        assert session.run(operator.add, 1, 2) == 3

    def test_run_with_func_error(self):
        session, _ = self.make_session_and_runner()

        def raise_value_error():
            raise ValueError("meep")

        with pytest.raises(nox.command.CommandFailed):
            assert session.run(raise_value_error)

    def test_run_install_only(self, caplog):
        caplog.set_level(logging.INFO)
        session, runner = self.make_session_and_runner()
        runner.global_config.install_only = True

        with mock.patch.object(nox.command, "run") as run:
            assert session.run("spam", "eggs") is None

        run.assert_not_called()

        assert "install-only" in caplog.text

    def test_run_install_only_should_install(self):
        session, runner = self.make_session_and_runner()
        runner.global_config.install_only = True

        with mock.patch.object(nox.command, "run") as run:
            session.install("spam")
            session.run("spam", "eggs")

        run.assert_called_once_with(
            ("python", "-m", "pip", "install", "spam"),
            env=mock.ANY,
            external=mock.ANY,
            paths=mock.ANY,
            silent=mock.ANY,
        )

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

    def test_run_external_not_a_virtualenv(self):
        # Non-virtualenv sessions should always allow external programs.
        session, runner = self.make_session_and_runner()

        runner.venv = nox.virtualenv.ProcessEnv()

        with mock.patch("nox.command.run", autospec=True) as run:
            session.run(sys.executable, "--version")

        run.assert_called_once_with(
            (sys.executable, "--version"), external=True, env=mock.ANY, paths=None
        )

    def test_run_external_condaenv(self):
        # condaenv sessions should always allow conda.
        session, runner = self.make_session_and_runner()
        runner.venv = mock.create_autospec(nox.virtualenv.CondaEnv)
        runner.venv.allowed_globals = ("conda",)
        runner.venv.env = {}
        runner.venv.bin_paths = ["/path/to/env/bin"]
        runner.venv.create.return_value = True

        with mock.patch("nox.command.run", autospec=True) as run:
            session.run("conda", "--version")

        run.assert_called_once_with(
            ("conda", "--version"),
            external=True,
            env=mock.ANY,
            paths=["/path/to/env/bin"],
        )

    def test_run_external_with_error_on_external_run(self):
        session, runner = self.make_session_and_runner()

        runner.global_config.error_on_external_run = True

        with pytest.raises(nox.command.CommandFailed, match="External"):
            session.run(sys.executable, "--version")

    def test_run_external_with_error_on_external_run_condaenv(self):
        session, runner = self.make_session_and_runner()
        runner.venv = mock.create_autospec(nox.virtualenv.CondaEnv)
        runner.venv.env = {}
        runner.venv.bin_paths = ["/path/to/env/bin"]

        runner.global_config.error_on_external_run = True

        with pytest.raises(nox.command.CommandFailed, match="External"):
            session.run(sys.executable, "--version")

    def test_run_always_bad_args(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(ValueError) as exc_info:
            session.run_always()

        exc_args = exc_info.value.args
        assert exc_args == ("At least one argument required to run_always().",)

    def test_run_always_success(self):
        session, _ = self.make_session_and_runner()

        assert session.run_always(operator.add, 1300, 37) == 1337

    def test_run_always_install_only(self, caplog):
        session, runner = self.make_session_and_runner()
        runner.global_config.install_only = True

        assert session.run_always(operator.add, 23, 19) == 42

    def test_conda_install_bad_args(self):
        session, runner = self.make_session_and_runner()
        runner.venv = mock.create_autospec(nox.virtualenv.CondaEnv)
        runner.venv.location = "dummy"

        with pytest.raises(ValueError, match="arg"):
            session.conda_install()

    def test_conda_install_bad_args_odd_nb_double_quotes(self):
        session, runner = self.make_session_and_runner()
        runner.venv = mock.create_autospec(nox.virtualenv.CondaEnv)
        runner.venv.location = "./not/a/location"

        with pytest.raises(ValueError, match="odd number of quotes"):
            session.conda_install('a"a')

    def test_conda_install_bad_args_cannot_escape(self):
        session, runner = self.make_session_and_runner()
        runner.venv = mock.create_autospec(nox.virtualenv.CondaEnv)
        runner.venv.location = "./not/a/location"

        with pytest.raises(ValueError, match="Cannot escape"):
            session.conda_install('a"o"<a')

    def test_conda_install_not_a_condaenv(self):
        session, runner = self.make_session_and_runner()

        runner.venv = None

        with pytest.raises(ValueError, match="conda environment"):
            session.conda_install()

    @pytest.mark.parametrize(
        "auto_offline", [False, True], ids="auto_offline={}".format
    )
    @pytest.mark.parametrize("offline", [False, True], ids="offline={}".format)
    def test_conda_install(self, auto_offline, offline):
        runner = nox.sessions.SessionRunner(
            name="test",
            signatures=["test"],
            func=mock.sentinel.func,
            global_config=_options.options.namespace(posargs=mock.sentinel.posargs),
            manifest=mock.create_autospec(nox.manifest.Manifest),
        )
        runner.venv = mock.create_autospec(nox.virtualenv.CondaEnv)
        runner.venv.location = "/path/to/conda/env"
        runner.venv.env = {}
        runner.venv.is_offline = lambda: offline

        class SessionNoSlots(nox.sessions.Session):
            pass

        session = SessionNoSlots(runner=runner)

        with mock.patch.object(session, "_run", autospec=True) as run:
            args = ("--offline",) if auto_offline and offline else ()
            session.conda_install("requests", "urllib3", auto_offline=auto_offline)
            run.assert_called_once_with(
                "conda",
                "install",
                "--yes",
                *args,
                "--prefix",
                "/path/to/conda/env",
                "requests",
                "urllib3",
                silent=True,
                external="error",
            )

    @pytest.mark.parametrize(
        "version_constraint",
        ["no", "yes", "already_dbl_quoted"],
        ids="version_constraint={}".format,
    )
    def test_conda_install_non_default_kwargs(self, version_constraint):
        runner = nox.sessions.SessionRunner(
            name="test",
            signatures=["test"],
            func=mock.sentinel.func,
            global_config=_options.options.namespace(posargs=mock.sentinel.posargs),
            manifest=mock.create_autospec(nox.manifest.Manifest),
        )
        runner.venv = mock.create_autospec(nox.virtualenv.CondaEnv)
        runner.venv.location = "/path/to/conda/env"
        runner.venv.env = {}
        runner.venv.is_offline = lambda: False

        class SessionNoSlots(nox.sessions.Session):
            pass

        session = SessionNoSlots(runner=runner)

        if version_constraint == "no":
            pkg_requirement = passed_arg = "urllib3"
        elif version_constraint == "yes":
            pkg_requirement = "urllib3<1.25"
            passed_arg = '"%s"' % pkg_requirement
        elif version_constraint == "already_dbl_quoted":
            pkg_requirement = passed_arg = '"urllib3<1.25"'
        else:
            raise ValueError(version_constraint)

        with mock.patch.object(session, "_run", autospec=True) as run:
            session.conda_install("requests", pkg_requirement, silent=False)
            run.assert_called_once_with(
                "conda",
                "install",
                "--yes",
                "--prefix",
                "/path/to/conda/env",
                "requests",
                # this will be double quoted if unquoted constraint is present
                passed_arg,
                silent=False,
                external="error",
            )

    def test_install_bad_args_no_arg(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(ValueError, match="arg"):
            session.install()

    def test_install_not_a_virtualenv(self):
        session, runner = self.make_session_and_runner()

        runner.venv = None

        with pytest.raises(ValueError, match="virtualenv"):
            session.install()

    def test_install(self):
        runner = nox.sessions.SessionRunner(
            name="test",
            signatures=["test"],
            func=mock.sentinel.func,
            global_config=_options.options.namespace(posargs=mock.sentinel.posargs),
            manifest=mock.create_autospec(nox.manifest.Manifest),
        )
        runner.venv = mock.create_autospec(nox.virtualenv.VirtualEnv)
        runner.venv.env = {}

        class SessionNoSlots(nox.sessions.Session):
            pass

        session = SessionNoSlots(runner=runner)

        with mock.patch.object(session, "_run", autospec=True) as run:
            session.install("requests", "urllib3")
            run.assert_called_once_with(
                "python",
                "-m",
                "pip",
                "install",
                "requests",
                "urllib3",
                silent=True,
                external="error",
            )

    def test_install_non_default_kwargs(self):
        runner = nox.sessions.SessionRunner(
            name="test",
            signatures=["test"],
            func=mock.sentinel.func,
            global_config=_options.options.namespace(posargs=mock.sentinel.posargs),
            manifest=mock.create_autospec(nox.manifest.Manifest),
        )
        runner.venv = mock.create_autospec(nox.virtualenv.VirtualEnv)
        runner.venv.env = {}

        class SessionNoSlots(nox.sessions.Session):
            pass

        session = SessionNoSlots(runner=runner)

        with mock.patch.object(session, "_run", autospec=True) as run:
            session.install("requests", "urllib3", silent=False)
            run.assert_called_once_with(
                "python",
                "-m",
                "pip",
                "install",
                "requests",
                "urllib3",
                silent=False,
                external="error",
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

        with pytest.raises(nox.sessions._SessionQuit, match="meep"):
            session.error("meep")

    def test_error_no_log(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(nox.sessions._SessionQuit):
            session.error()

    def test_skip_no_log(self):
        session, _ = self.make_session_and_runner()

        with pytest.raises(nox.sessions._SessionSkip):
            session.skip()

    def test___slots__(self):
        session, _ = self.make_session_and_runner()
        with pytest.raises(AttributeError):
            session.foo = "bar"
        with pytest.raises(AttributeError):
            session.quux

    def test___dict__(self):
        session, _ = self.make_session_and_runner()
        expected = {name: getattr(session, name) for name in session.__slots__}
        assert session.__dict__ == expected


class TestSessionRunner:
    def make_runner(self):
        func = mock.Mock()
        func.python = None
        func.venv_backend = None
        func.reuse_venv = False
        runner = nox.sessions.SessionRunner(
            name="test",
            signatures=["test(1, 2)"],
            func=func,
            global_config=_options.options.namespace(
                noxfile=os.path.join(os.getcwd(), "noxfile.py"),
                envdir="envdir",
                posargs=mock.sentinel.posargs,
                reuse_existing_virtualenvs=False,
                error_on_missing_interpreters=False,
            ),
            manifest=mock.create_autospec(nox.manifest.Manifest),
        )
        return runner

    def test_properties(self):
        runner = self.make_runner()

        assert runner.name == "test"
        assert runner.signatures == ["test(1, 2)"]
        assert runner.func is not None
        assert callable(runner.func)
        assert isinstance(runner.description, str)
        assert runner.global_config.posargs == mock.sentinel.posargs
        assert isinstance(runner.manifest, nox.manifest.Manifest)

    def test_str_and_friendly_name(self):
        runner = self.make_runner()
        runner.signatures = ["test(1, 2)", "test(3, 4)"]

        assert str(runner) == "Session(name=test, signatures=test(1, 2), test(3, 4))"
        assert runner.friendly_name == "test(1, 2)"

    def test_description_property_one_line(self):
        def foo():
            """Just one line"""

        runner = self.make_runner()
        runner.func = foo
        assert runner.description == "Just one line"

    def test_description_property_multi_line(self):
        def foo():
            """
            Multiline

            Extra description
            """

        runner = self.make_runner()
        runner.func = foo
        assert runner.description == "Multiline"

    def test_description_property_no_doc(self):
        def foo():
            pass

        runner = self.make_runner()
        runner.func = foo
        assert runner.description is None

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

    @pytest.mark.parametrize(
        "create_method,venv_backend,expected_backend",
        [
            ("nox.virtualenv.VirtualEnv.create", None, nox.virtualenv.VirtualEnv),
            (
                "nox.virtualenv.VirtualEnv.create",
                "virtualenv",
                nox.virtualenv.VirtualEnv,
            ),
            ("nox.virtualenv.VirtualEnv.create", "venv", nox.virtualenv.VirtualEnv),
            ("nox.virtualenv.CondaEnv.create", "conda", nox.virtualenv.CondaEnv),
        ],
    )
    def test__create_venv_options(self, create_method, venv_backend, expected_backend):
        runner = self.make_runner()
        runner.func.python = "coolpython"
        runner.func.reuse_venv = True
        runner.func.venv_backend = venv_backend

        with mock.patch(create_method, autospec=True) as create:
            runner._create_venv()

        create.assert_called_once_with(runner.venv)
        assert isinstance(runner.venv, expected_backend)
        assert runner.venv.interpreter == "coolpython"
        assert runner.venv.reuse_existing is True

    def test__create_venv_unexpected_venv_backend(self):
        runner = self.make_runner()
        runner.func.venv_backend = "somenewenvtool"

        with pytest.raises(ValueError, match="venv_backend"):
            runner._create_venv()

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

    def test_execute_with_manifest_null_session_func(self):
        runner = self.make_runner()
        runner.func = nox.manifest._null_session_func

        result = runner.execute()

        assert result.status == nox.sessions.Status.SKIPPED
        assert "no parameters" in result.reason

    def test_execute_skip_missing_interpreter(self):
        runner = self.make_runner_with_mock_venv()
        runner._create_venv.side_effect = nox.virtualenv.InterpreterNotFound("meep")

        result = runner.execute()

        assert result.status == nox.sessions.Status.SKIPPED
        assert "meep" in result.reason

    def test_execute_error_missing_interpreter(self):
        runner = self.make_runner_with_mock_venv()
        runner.global_config.error_on_missing_interpreters = True
        runner._create_venv.side_effect = nox.virtualenv.InterpreterNotFound("meep")

        result = runner.execute()

        assert result.status == nox.sessions.Status.FAILED
        assert "meep" in result.reason

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
        result = nox.sessions.Result(
            object(), nox.sessions.Status.FAILED, reason="meep"
        )
        assert result.imperfect == "failed: meep"

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
                signatures=["siggy"], name="namey", func=mock.Mock()
            ),
            status=nox.sessions.Status.SUCCESS,
        )
        answer = result.serialize()
        assert answer["name"] == "namey"
        assert answer["result"] == "success"
        assert answer["result_code"] == 1
        assert answer["signatures"] == ["siggy"]
