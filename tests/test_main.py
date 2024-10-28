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

from __future__ import annotations

import contextlib
import os
import sys
from importlib import metadata
from pathlib import Path
from unittest import mock

import pytest

import nox
import nox.__main__
import nox._options
import nox.registry
import nox.sessions

RESOURCES = os.path.join(os.path.dirname(__file__), "resources")
VERSION = metadata.version("nox")


# This is needed because CI systems will mess up these tests due to the
# way Nox handles the --session parameter's default value. This avoids that
# mess.
os.environ.pop("NOXSESSION", None)


def test_main_no_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.executable])
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the config looks correct.
        config = execute.call_args[1]["global_config"]
        assert config.noxfile == "noxfile.py"
        assert config.sessions is None
        assert not config.no_venv
        assert not config.reuse_existing_virtualenvs
        assert not config.reuse_venv
        assert not config.stop_on_first_error
        assert config.posargs == []


def test_main_long_form_args():
    sys.argv = [
        sys.executable,
        "--noxfile",
        "noxfile.py",
        "--envdir",
        ".other",
        "--sessions",
        "1",
        "2",
        "--default-venv-backend",
        "venv",
        "--force-venv-backend",
        "none",
        "--no-venv",
        "--reuse-existing-virtualenvs",
        "--stop-on-first-error",
    ]
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the config looks correct.
        config = execute.call_args[1]["global_config"]
        assert config.noxfile == "noxfile.py"
        assert config.envdir.endswith(".other")
        assert config.sessions == ["1", "2"]
        assert config.default_venv_backend == "venv"
        assert config.force_venv_backend == "none"
        assert config.no_venv is True
        assert config.reuse_existing_virtualenvs is True
        assert config.reuse_venv == "yes"
        assert config.stop_on_first_error is True
        assert config.posargs == []


def test_main_no_venv(monkeypatch, capsys):
    # Check that --no-venv overrides force_venv_backend
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nox",
            "--noxfile",
            os.path.join(RESOURCES, "noxfile_pythons.py"),
            "--no-venv",
            "-s",
            "snack(cheese='cheddar')",
        ],
    )

    with mock.patch("sys.exit") as sys_exit:
        nox.__main__.main()
        stdout, stderr = capsys.readouterr()
        assert stdout == "Noms, cheddar so good!\n"
        assert (
            "Session snack is set to run with venv_backend='none', IGNORING its python"
            in stderr
        )
        assert "Session snack(cheese='cheddar') was successful." in stderr
        sys_exit.assert_called_once_with(0)


def test_main_no_venv_error():
    # Check that --no-venv can not be set together with a non-none --force-venv-backend
    sys.argv = [
        sys.executable,
        "--noxfile",
        "noxfile.py",
        "--force-venv-backend",
        "conda",
        "--no-venv",
    ]
    with pytest.raises(ValueError, match="You can not use"):
        nox.__main__.main()


def test_main_short_form_args(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            sys.executable,
            "-f",
            "noxfile.py",
            "-s",
            "1",
            "2",
            "-db",
            "venv",
            "-fb",
            "conda",
            "-r",
        ],
    )
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the config looks correct.
        config = execute.call_args[1]["global_config"]
        assert config.noxfile == "noxfile.py"
        assert config.sessions == ["1", "2"]
        assert config.default_venv_backend == "venv"
        assert config.force_venv_backend == "conda"
        assert config.reuse_existing_virtualenvs is True
        assert config.reuse_venv == "yes"


def test_main_explicit_sessions(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.executable, "-e", "1", "2"])
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the explicit sessions are listed in the config.
        config = execute.call_args[1]["global_config"]
        assert config.sessions == ["1", "2"]


def test_main_explicit_sessions_with_spaces_in_names(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", [sys.executable, "-e", "unit tests", "the unit tests"]
    )
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the explicit sessions are listed in the config.
        config = execute.call_args[1]["global_config"]
        assert config.sessions == ["unit tests", "the unit tests"]


@pytest.mark.parametrize(
    "var,option,env,values",
    [
        ("NOXSESSION", "sessions", "foo", ["foo"]),
        ("NOXSESSION", "sessions", "foo,bar", ["foo", "bar"]),
        ("NOXPYTHON", "pythons", "3.9", ["3.9"]),
        ("NOXPYTHON", "pythons", "3.9,3.10", ["3.9", "3.10"]),
        ("NOXEXTRAPYTHON", "extra_pythons", "3.9", ["3.9"]),
        ("NOXEXTRAPYTHON", "extra_pythons", "3.9,3.10", ["3.9", "3.10"]),
        ("NOXFORCEPYTHON", "force_pythons", "3.9", ["3.9"]),
        ("NOXFORCEPYTHON", "force_pythons", "3.9,3.10", ["3.9", "3.10"]),
    ],
    ids=[
        "single_session",
        "multiple_sessions",
        "single_python",
        "multiple_pythons",
        "single_extra_python",
        "multiple_extra_pythons",
        "single_force_python",
        "multiple_force_pythons",
    ],
)
def test_main_list_option_from_nox_env_var(monkeypatch, var, option, env, values):
    monkeypatch.setenv(var, env)
    monkeypatch.setattr(sys, "argv", [sys.executable])

    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the sessions from the env var are listed in the config.
        config = execute.call_args[1]["global_config"]
        config_values = getattr(config, option)
        assert len(config_values) == len(values)
        assert all(value in config_values for value in values)


@pytest.mark.parametrize(
    "options,env,expected",
    [
        (["--default-venv-backend", "conda"], "", "conda"),
        ([], "mamba", "mamba"),
        (["--default-venv-backend", "conda"], "mamba", "conda"),
    ],
    ids=["option", "env", "option_over_env"],
)
def test_default_venv_backend_option(monkeypatch, options, env, expected):
    monkeypatch.setenv("NOX_DEFAULT_VENV_BACKEND", env)
    monkeypatch.setattr(sys, "argv", [sys.executable, *options])
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the default venv backend is set in the config.
        config = execute.call_args[1]["global_config"]
        assert config.default_venv_backend == expected


def test_main_positional_args(capsys, monkeypatch):
    fake_exit = mock.Mock(side_effect=ValueError("asdf!"))

    monkeypatch.setattr(sys, "argv", [sys.executable, "1", "2", "3"])
    with mock.patch.object(sys, "exit", fake_exit), pytest.raises(
        ValueError, match="asdf!"
    ):
        nox.__main__.main()
    _, stderr = capsys.readouterr()
    assert "Unknown argument(s) '1 2 3'" in stderr
    fake_exit.assert_called_once_with(2)

    fake_exit.reset_mock()
    monkeypatch.setattr(sys, "argv", [sys.executable, "1", "2", "3", "--"])
    with mock.patch.object(sys, "exit", fake_exit), pytest.raises(
        ValueError, match="asdf!"
    ):
        nox.__main__.main()
    _, stderr = capsys.readouterr()
    assert "Unknown argument(s) '1 2 3'" in stderr
    fake_exit.assert_called_once_with(2)


def test_main_positional_with_double_hyphen(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.executable, "--", "1", "2", "3"])
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the positional args are listed in the config.
        config = execute.call_args[1]["global_config"]
        assert config.posargs == ["1", "2", "3"]


def test_main_positional_flag_like_with_double_hyphen(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", [sys.executable, "--", "1", "2", "3", "-f", "--baz"]
    )
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the positional args are listed in the config.
        config = execute.call_args[1]["global_config"]
        assert config.posargs == ["1", "2", "3", "-f", "--baz"]


def test_main_version(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.executable, "--version"])

    with contextlib.ExitStack() as stack:
        execute = stack.enter_context(mock.patch("nox.workflow.execute"))
        exit_mock = stack.enter_context(mock.patch("sys.exit"))
        nox.__main__.main()
        _, err = capsys.readouterr()
        assert VERSION in err
        exit_mock.assert_not_called()
        execute.assert_not_called()


def test_main_help(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.executable, "--help"])

    with contextlib.ExitStack() as stack:
        execute = stack.enter_context(mock.patch("nox.workflow.execute"))
        exit_mock = stack.enter_context(mock.patch("sys.exit"))
        nox.__main__.main()
        out, _ = capsys.readouterr()
        assert "help" in out
        exit_mock.assert_not_called()
        execute.assert_not_called()


def test_main_failure(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.executable])
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 1
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(1)


def test_main_nested_config(capsys, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nox",
            "--noxfile",
            os.path.join(RESOURCES, "noxfile_nested.py"),
            "-s",
            "snack(cheese='cheddar')",
        ],
    )

    with mock.patch("sys.exit") as sys_exit:
        nox.__main__.main()
        stdout, stderr = capsys.readouterr()
        assert stdout == "Noms, cheddar so good!\n"
        assert "Session snack(cheese='cheddar') was successful." in stderr
        sys_exit.assert_called_once_with(0)


def test_main_session_with_names(capsys, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nox",
            "--noxfile",
            os.path.join(RESOURCES, "noxfile_spaces.py"),
            "-s",
            "cheese list(cheese='cheddar')",
        ],
    )

    with mock.patch("sys.exit") as sys_exit:
        nox.__main__.main()
        stdout, stderr = capsys.readouterr()
        assert stdout == "Noms, cheddar so good!\n"
        assert "Session cheese list(cheese='cheddar') was successful." in stderr
        sys_exit.assert_called_once_with(0)


@pytest.fixture
def run_nox(capsys, monkeypatch):
    def _run_nox(*args):
        monkeypatch.setattr(sys, "argv", ["nox", *args])

        with mock.patch("sys.exit") as sys_exit:
            nox.__main__.main()
            stdout, stderr = capsys.readouterr()
            returncode = sys_exit.call_args[0][0]

        return returncode, stdout, stderr

    return _run_nox


@pytest.mark.parametrize(
    ("normalized_name", "session"),
    [
        ("test(arg='Jane')", "test(arg='Jane')"),
        ("test(arg='Jane')", 'test(arg="Jane")'),
        ("test(arg='Jane')", 'test(arg = "Jane")'),
        ("test(arg='Jane')", 'test ( arg = "Jane" )'),
        ('test(arg="Joe\'s")', 'test(arg="Joe\'s")'),
        ('test(arg="Joe\'s")', "test(arg='Joe\\'s')"),
        ("test(arg='\"hello world\"')", "test(arg='\"hello world\"')"),
        ("test(arg='\"hello world\"')", 'test(arg="\\"hello world\\"")'),
        ("test(arg=[42])", "test(arg=[42])"),
        ("test(arg=[42])", "test(arg=[42,])"),
        ("test(arg=[42])", "test(arg=[ 42 ])"),
        ("test(arg=[42])", "test(arg=[0x2a])"),
        (
            "test(arg=datetime.datetime(1980, 1, 1, 0, 0))",
            "test(arg=datetime.datetime(1980, 1, 1, 0, 0))",
        ),
        (
            "test(arg=datetime.datetime(1980, 1, 1, 0, 0))",
            "test(arg=datetime.datetime(1980,1,1,0,0))",
        ),
        (
            "test(arg=datetime.datetime(1980, 1, 1, 0, 0))",
            "test(arg=datetime.datetime(1980, 1, 1, 0, 0x0))",
        ),
    ],
)
def test_main_with_normalized_session_names(run_nox, normalized_name, session):
    noxfile = os.path.join(RESOURCES, "noxfile_normalization.py")
    returncode, _, stderr = run_nox(f"--noxfile={noxfile}", f"--session={session}")
    assert returncode == 0
    assert normalized_name in stderr


@pytest.mark.parametrize(
    "session",
    [
        "syntax error",
        "test(arg=Jane)",
        "test(arg='Jane ')",
        "_test(arg='Jane')",
        "test(arg=42)",
        "test(arg=[42.0])",
        "test(arg=[43])",
        "test(arg=<user_nox_module.Foo object at 0x123456789abc>)",
        "test(arg=datetime.datetime(1980, 1, 1))",
    ],
)
def test_main_with_bad_session_names(run_nox, session):
    noxfile = os.path.join(RESOURCES, "noxfile_normalization.py")
    returncode, _, stderr = run_nox(f"--noxfile={noxfile}", f"--session={session}")
    assert returncode != 0
    assert session in stderr


def test_main_noxfile_options(monkeypatch, generate_noxfile_options):
    noxfile_path = generate_noxfile_options(reuse_existing_virtualenvs=True)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nox",
            "-l",
            "-s",
            "test",
            "--noxfile",
            noxfile_path,
        ],
    )

    with mock.patch("nox.tasks.honor_list_request") as honor_list_request:
        honor_list_request.return_value = 0

        with mock.patch("sys.exit"):
            nox.__main__.main()

        assert honor_list_request.called

        # Verify that the config looks correct.
        config = honor_list_request.call_args[1]["global_config"]
        assert config.reuse_existing_virtualenvs is True
        assert config.reuse_venv == "yes"


def test_main_noxfile_options_disabled_by_flag(monkeypatch, generate_noxfile_options):
    noxfile_path = generate_noxfile_options(reuse_existing_virtualenvs=True)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nox",
            "-l",
            "-s",
            "test",
            "--no-reuse-existing-virtualenvs",
            "--noxfile",
            noxfile_path,
        ],
    )

    with mock.patch("nox.tasks.honor_list_request") as honor_list_request:
        honor_list_request.return_value = 0

        with mock.patch("sys.exit"):
            nox.__main__.main()

        assert honor_list_request.called

        # Verify that the config looks correct.
        config = honor_list_request.call_args[1]["global_config"]
        assert config.reuse_existing_virtualenvs is False
        assert config.reuse_venv == "no"


def test_main_noxfile_options_sessions(monkeypatch, generate_noxfile_options):
    noxfile_path = generate_noxfile_options(reuse_existing_virtualenvs=True)
    monkeypatch.setattr(
        sys,
        "argv",
        ["nox", "-l", "--noxfile", noxfile_path],
    )

    with mock.patch("nox.tasks.honor_list_request") as honor_list_request:
        honor_list_request.return_value = 0

        with mock.patch("sys.exit"):
            nox.__main__.main()

        assert honor_list_request.called

        # Verify that the config looks correct.
        config = honor_list_request.call_args[1]["global_config"]
        assert config.sessions == ["test"]


@pytest.fixture
def generate_noxfile_options_pythons(tmp_path):
    """Generate noxfile.py with test and launch_rocket sessions.

    The sessions are defined for both the default and alternate Python versions.
    The ``default_session`` and ``default_python`` parameters determine what
    goes into ``nox.options.sessions`` and ``nox.options.pythons``, respectively.
    """

    def generate_noxfile(default_session, default_python, alternate_python):
        path = Path(RESOURCES) / "noxfile_options_pythons.py"
        text = path.read_text()
        text = text.format(
            default_session=default_session,
            default_python=default_python,
            alternate_python=alternate_python,
        )
        path = tmp_path / "noxfile.py"
        path.write_text(text)
        return str(path)

    return generate_noxfile


python_current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
python_next_version = f"{sys.version_info.major}.{sys.version_info.minor + 1}"


def test_main_noxfile_options_with_pythons_override(
    capsys, monkeypatch, generate_noxfile_options_pythons
):
    noxfile = generate_noxfile_options_pythons(
        default_session="test",
        default_python=python_next_version,
        alternate_python=python_current_version,
    )

    monkeypatch.setattr(
        sys, "argv", ["nox", "--noxfile", noxfile, "--python", python_current_version]
    )

    with mock.patch("sys.exit") as sys_exit:
        nox.__main__.main()
        _, stderr = capsys.readouterr()
        sys_exit.assert_called_once_with(0)

    for python_version in [python_current_version, python_next_version]:
        for session in ["test", "launch_rocket"]:
            line = f"Running session {session}-{python_version}"
            if session == "test" and python_version == python_current_version:
                assert line in stderr
            else:
                assert line not in stderr


def test_main_noxfile_options_with_sessions_override(
    capsys, monkeypatch, generate_noxfile_options_pythons
):
    noxfile = generate_noxfile_options_pythons(
        default_session="test",
        default_python=python_current_version,
        alternate_python=python_next_version,
    )

    monkeypatch.setattr(
        sys, "argv", ["nox", "--noxfile", noxfile, "--session", "launch_rocket"]
    )

    with mock.patch("sys.exit") as sys_exit:
        nox.__main__.main()
        _, stderr = capsys.readouterr()
        sys_exit.assert_called_once_with(0)

    for python_version in [python_current_version, python_next_version]:
        for session in ["test", "launch_rocket"]:
            line = f"Running session {session}-{python_version}"
            if session == "launch_rocket" and python_version == python_current_version:
                assert line in stderr
            else:
                assert line not in stderr


@pytest.mark.parametrize(("isatty_value", "expected"), [(True, True), (False, False)])
def test_main_color_from_isatty(monkeypatch, isatty_value, expected):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr(sys, "argv", [sys.executable])
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0
        with mock.patch("sys.stdout.isatty") as isatty:
            isatty.return_value = isatty_value

            # Call the main function.
            with mock.patch.object(sys, "exit"):
                nox.__main__.main()

            config = execute.call_args[1]["global_config"]
            assert config.color == expected


@pytest.mark.parametrize(
    ("color_opt", "expected"),
    [
        ("--forcecolor", True),
        ("--nocolor", False),
        ("--force-color", True),
        ("--no-color", False),
    ],
)
def test_main_color_options(monkeypatch, color_opt, expected):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr(sys, "argv", [sys.executable, color_opt])
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit"):
            nox.__main__.main()

        config = execute.call_args[1]["global_config"]
        assert config.color == expected


def test_main_color_conflict(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.executable, "--forcecolor", "--nocolor"])
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 1

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_with(1)

    _, err = capsys.readouterr()

    assert "color" in err


def test_main_force_python(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["nox", "--force-python=3.11"])
    with mock.patch("nox.workflow.execute", return_value=0) as execute:
        with mock.patch.object(sys, "exit"):
            nox.__main__.main()
        config = execute.call_args[1]["global_config"]
    assert config.pythons == config.extra_pythons == ["3.11"]


def test_main_reuse_existing_virtualenvs_no_install(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["nox", "-R"])
    with mock.patch("nox.workflow.execute", return_value=0) as execute:
        with mock.patch.object(sys, "exit"):
            nox.__main__.main()
        config = execute.call_args[1]["global_config"]
    assert (
        config.reuse_existing_virtualenvs
        and config.no_install
        and config.reuse_venv == "yes"
    )


@pytest.mark.parametrize(
    ("should_set_ci_env_var", "noxfile_option_value", "expected_final_value"),
    [
        (True, None, True),
        (True, True, True),
        (True, False, False),
        (False, None, False),
        (False, True, True),
        (False, False, False),
    ],
)
def test_main_noxfile_options_with_ci_override(
    monkeypatch,
    generate_noxfile_options,
    should_set_ci_env_var,
    noxfile_option_value,
    expected_final_value,
):
    monkeypatch.delenv("CI", raising=False)  # make sure we have a clean environment
    if should_set_ci_env_var:
        monkeypatch.setenv("CI", "True")
    # Reload nox.options taking into consideration monkeypatch.{delenv|setenv}
    monkeypatch.setattr(
        nox._options, "noxfile_options", nox._options.options.noxfile_namespace()
    )
    monkeypatch.setattr(nox, "options", nox._options.noxfile_options)

    if noxfile_option_value is None:
        noxfile_path = generate_noxfile_options()
    else:
        noxfile_path = generate_noxfile_options(
            error_on_missing_interpreters=noxfile_option_value
        )

    monkeypatch.setattr(
        sys,
        "argv",
        ["nox", "-l", "--noxfile", str(noxfile_path)],
    )

    with mock.patch(
        "nox.tasks.honor_list_request", return_value=0
    ) as honor_list_request:
        with mock.patch("sys.exit"):
            nox.__main__.main()
        config = honor_list_request.call_args[1]["global_config"]
    assert config.error_on_missing_interpreters == expected_final_value


@pytest.mark.parametrize(
    "reuse_venv",
    [
        "yes",
        "no",
        "always",
        "never",
    ],
)
def test_main_reuse_venv_cli_flags(monkeypatch, generate_noxfile_options, reuse_venv):
    monkeypatch.setattr(sys, "argv", ["nox", "--reuse-venv", reuse_venv])
    with mock.patch("nox.workflow.execute", return_value=0) as execute:
        with mock.patch.object(sys, "exit"):
            nox.__main__.main()
        config = execute.call_args[1]["global_config"]
    assert (
        not config.reuse_existing_virtualenvs
    )  # should remain unaffected in this case
    assert config.reuse_venv == reuse_venv


@pytest.mark.parametrize(
    ("reuse_venv", "reuse_existing_virtualenvs", "expected"),
    [
        ("yes", None, "yes"),
        ("yes", False, "yes"),
        ("yes", True, "yes"),
        ("yes", "--no-reuse-existing-virtualenvs", "no"),
        ("yes", "--reuse-existing-virtualenvs", "yes"),
        ("no", None, "no"),
        ("no", False, "no"),
        ("no", True, "yes"),
        ("no", "--no-reuse-existing-virtualenvs", "no"),
        ("no", "--reuse-existing-virtualenvs", "yes"),
        ("always", None, "always"),
        ("always", False, "always"),
        ("always", True, "yes"),
        ("always", "--no-reuse-existing-virtualenvs", "no"),
        ("always", "--reuse-existing-virtualenvs", "yes"),
        ("never", None, "never"),
        ("never", False, "never"),
        ("never", True, "yes"),
        ("never", "--no-reuse-existing-virtualenvs", "no"),
        ("never", "--reuse-existing-virtualenvs", "yes"),
    ],
)
def test_main_noxfile_options_reuse_venv_compat_check(
    monkeypatch,
    generate_noxfile_options,
    reuse_venv,
    reuse_existing_virtualenvs,
    expected,
):
    cmd_args = ["nox", "-l"]
    # CLI Compat Check
    if isinstance(reuse_existing_virtualenvs, str):
        cmd_args += [reuse_existing_virtualenvs]

    # Generate noxfile
    if isinstance(reuse_existing_virtualenvs, bool):
        # Non-CLI Compat Check
        noxfile_path = generate_noxfile_options(
            reuse_venv=reuse_venv, reuse_existing_virtualenvs=reuse_existing_virtualenvs
        )
    else:
        noxfile_path = generate_noxfile_options(reuse_venv=reuse_venv)
    cmd_args += ["--noxfile", str(noxfile_path)]

    # Reset nox.options
    monkeypatch.setattr(
        nox._options, "noxfile_options", nox._options.options.noxfile_namespace()
    )
    monkeypatch.setattr(nox, "options", nox._options.noxfile_options)

    # Execute
    monkeypatch.setattr(sys, "argv", cmd_args)
    with mock.patch(
        "nox.tasks.honor_list_request", return_value=0
    ) as honor_list_request:
        with mock.patch("sys.exit"):
            nox.__main__.main()
        config = honor_list_request.call_args[1]["global_config"]
    assert config.reuse_venv == expected


def test_noxfile_options_cant_be_set():
    with pytest.raises(AttributeError, match="reuse_venvs"):
        nox.options.reuse_venvs = True


def test_noxfile_options_cant_be_set_long():
    with pytest.raises(AttributeError, match="i_am_clearly_not_an_option"):
        nox.options.i_am_clearly_not_an_option = True
