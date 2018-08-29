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
import os
import sys
from unittest import mock

import contexter
import pkg_resources
import pytest

import nox
import nox.__main__
import nox.registry
import nox.sessions


RESOURCES = os.path.join(os.path.dirname(__file__), "resources")
VERSION = pkg_resources.get_distribution("nox").version


def test_global_config_constructor():
    args = argparse.Namespace(
        noxfile="noxfile",
        envdir="dir",
        sessions=["1", "2"],
        keywords="red and blue",
        list_sessions=False,
        reuse_existing_virtualenvs=True,
        stop_on_first_error=False,
        posargs=["a", "b", "c"],
        report=None,
    )

    config = nox.__main__.GlobalConfig(args)

    assert config.noxfile == "noxfile"
    assert config.envdir == os.path.abspath("dir")
    assert config.sessions == ["1", "2"]
    assert config.keywords == "red and blue"
    assert config.list_sessions is False
    assert config.reuse_existing_virtualenvs is True
    assert config.stop_on_first_error is False
    assert config.posargs == ["a", "b", "c"]

    args.posargs = ["--", "a", "b", "c"]
    config = nox.__main__.GlobalConfig(args)
    assert config.posargs == ["a", "b", "c"]


def test_main_no_args():
    sys.argv = [sys.executable]
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
        assert config.envdir.endswith(".nox")
        assert config.sessions is None
        assert config.reuse_existing_virtualenvs is False
        assert config.stop_on_first_error is False
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
        assert config.reuse_existing_virtualenvs is True
        assert config.stop_on_first_error is True
        assert config.posargs == []


def test_main_short_form_args():
    sys.argv = [sys.executable, "-f", "noxfile.py", "-s", "1", "2", "-r"]
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
        assert config.reuse_existing_virtualenvs is True


def test_main_explicit_sessions():
    sys.argv = [sys.executable, "-e", "1", "2"]
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


@pytest.mark.parametrize(
    "env,sessions", [("foo", ["foo"]), ("foo,bar", ["foo", "bar"])]
)
def test_main_session_from_nox_env_var(env, sessions):
    os.environ["NOXSESSION"] = env
    sys.argv = [sys.executable]
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 0

        # Call the main function.
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(0)
        assert execute.called

        # Verify that the sessions from the env var are listed in the config.
        config = execute.call_args[1]["global_config"]
        assert len(config.sessions) == len(sessions)
        for session in sessions:
            assert session in config.sessions


def test_main_positional_args():
    sys.argv = [sys.executable, "1", "2", "3"]
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


def test_main_positional_with_double_hyphen():
    sys.argv = [sys.executable, "--", "1", "2", "3"]
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


def test_main_positional_flag_like_with_double_hyphen():
    sys.argv = [sys.executable, "--", "1", "2", "3", "-f", "--baz"]
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


def test_main_version(capsys):
    sys.argv = [sys.executable, "--version"]

    with contexter.ExitStack() as stack:
        execute = stack.enter_context(mock.patch("nox.workflow.execute"))
        exit_mock = stack.enter_context(mock.patch("sys.exit"))
        nox.__main__.main()
        _, err = capsys.readouterr()
        assert VERSION in err
        exit_mock.assert_not_called()
        execute.assert_not_called()


def test_main_failure():
    sys.argv = [sys.executable]
    with mock.patch("nox.workflow.execute") as execute:
        execute.return_value = 1
        with mock.patch.object(sys, "exit") as exit:
            nox.__main__.main()
            exit.assert_called_once_with(1)


def test_main_nested_config(capsys):
    sys.argv = [
        "nox",
        "--noxfile",
        os.path.join(RESOURCES, "noxfile_nested.py"),
        "-s",
        "snack(cheese='cheddar')",
    ]

    with mock.patch("sys.exit") as sys_exit:
        nox.__main__.main()
        stdout, stderr = capsys.readouterr()
        assert stdout == "Noms, cheddar so good!\n"
        assert "Session snack(cheese='cheddar') was successful." in stderr
        sys_exit.assert_called_once_with(0)
