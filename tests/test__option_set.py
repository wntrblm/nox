# Copyright 2019 Alethea Katherine Flowers
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

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nox import _option_set, _options

if TYPE_CHECKING:
    import argparse

# The vast majority of _option_set is tested by test_main, but the test helper
# :func:`OptionSet.namespace` needs a bit of help to get to full coverage.


RESOURCES = Path(__file__).parent.joinpath("resources")


class TestOptionSet:
    def test_namespace(self) -> None:
        optionset = _option_set.OptionSet()
        optionset.add_groups(_option_set.OptionGroup("group_a"))
        optionset.add_options(
            _option_set.Option(
                "option_a", group=optionset.groups["group_a"], default="meep"
            )
        )

        namespace = optionset.namespace()

        assert hasattr(namespace, "option_a")
        assert not hasattr(namespace, "non_existent_option")
        assert namespace.option_a == "meep"

    def test_namespace_values(self) -> None:
        optionset = _option_set.OptionSet()
        optionset.add_groups(_option_set.OptionGroup("group_a"))
        optionset.add_options(
            _option_set.Option(
                "option_a", group=optionset.groups["group_a"], default="meep"
            )
        )

        namespace = optionset.namespace(option_a="moop")

        assert namespace.option_a == "moop"

    def test_namespace_non_existent_options_with_values(self) -> None:
        optionset = _option_set.OptionSet()

        with pytest.raises(KeyError):
            optionset.namespace(non_existent_option="meep")

    def test_parser_hidden_option(self) -> None:
        optionset = _option_set.OptionSet()
        optionset.add_options(
            _option_set.Option(
                "oh_boy_i_am_hidden", hidden=True, group=None, default="meep"
            )
        )

        parser = optionset.parser()
        namespace = parser.parse_args([])
        optionset._finalize_args(namespace)

        assert namespace.oh_boy_i_am_hidden == "meep"

    def test_parser_groupless_option(self) -> None:
        optionset = _option_set.OptionSet()
        optionset.add_options(
            _option_set.Option("oh_no_i_have_no_group", group=None, default="meep")
        )

        with pytest.raises(
            ValueError,
            match="Option oh_no_i_have_no_group must either have a group or be hidden",
        ):
            optionset.parser()

    def test_session_completer(self) -> None:
        parsed_args = _options.options.namespace(
            posargs=[],
            noxfile=str(RESOURCES.joinpath("noxfile_multiple_sessions.py")),
        )
        actual_sessions_from_file = _options._session_completer(
            prefix="", parsed_args=parsed_args
        )

        expected_sessions = ["testytest", "lintylint", "typeytype"]
        assert expected_sessions == list(actual_sessions_from_file)

    def test_session_completer_invalid_sessions(self) -> None:
        parsed_args = _options.options.namespace(
            sessions=("baz",), keywords=(), posargs=[]
        )
        all_nox_sessions = _options._session_completer(
            prefix="", parsed_args=parsed_args
        )
        assert len(list(all_nox_sessions)) == 0

    def test_python_completer(self) -> None:
        parsed_args = _options.options.namespace(
            posargs=[],
            noxfile=str(RESOURCES.joinpath("noxfile_pythons.py")),
        )
        actual_pythons_from_file = _options._python_completer(
            prefix="", parsed_args=parsed_args
        )

        expected_pythons = {"3.6", "3.12"}
        assert expected_pythons == set(actual_pythons_from_file)

    def test_tag_completer(self) -> None:
        parsed_args = _options.options.namespace(
            posargs=[],
            noxfile=str(RESOURCES.joinpath("noxfile_tags.py")),
        )
        actual_tags_from_file = _options._tag_completer(
            prefix="", parsed_args=parsed_args
        )

        expected_tags = {f"tag{n}" for n in range(1, 8)}
        assert expected_tags == set(actual_tags_from_file)

    def test_validation_options(self) -> None:
        options = _option_set.NoxOptions(
            default_venv_backend=None,
            download_python="auto",
            envdir=None,
            error_on_external_run=False,
            error_on_missing_interpreters=False,
            force_venv_backend=None,
            keywords=None,
            pythons=None,
            report=None,
            reuse_existing_virtualenvs=False,
            reuse_venv=None,
            sessions=None,
            stop_on_first_error=False,
            tags=None,
            verbose=False,
        )
        options.sessions = ["testytest"]
        options.sessions = ("testytest",)
        with pytest.raises(ValueError):  # noqa: PT011
            options.sessions = "testytest"

        options.envdir = "envdir"
        options.envdir = Path("envdir")


class TestMerge:
    def parse_and_merge(
        self, args: list[str], noxfile_config: _option_set.NoxOptions
    ) -> argparse.Namespace:
        config = _options.options.parse_args(args)
        _options.options.merge_namespaces(config, noxfile_config)
        return config

    def test_noxfile_beats_default(self) -> None:
        noxfile_config = _options.options.noxfile_namespace()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge([], noxfile_config)

        assert config.sessions == ["lint"]

    def test_cli_beats_noxfile(self) -> None:
        noxfile_config = _options.options.noxfile_namespace()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge(["-s", "test"], noxfile_config)

        assert config.sessions == ["test"]

    def test_cli_reuse_venv_beats_noxfile_alias(self) -> None:
        """An explicit CLI --reuse-venv wins over the noxfile's legacy
        reuse_existing_virtualenvs alias (this used to be reversed)."""
        noxfile_config = _options.options.noxfile_namespace()
        noxfile_config.reuse_existing_virtualenvs = True
        config = self.parse_and_merge(["--reuse-venv", "never"], noxfile_config)

        assert config.reuse_venv == "never"

    def test_bare_sessions_flag_beats_noxfile(self) -> None:
        """An explicit but empty -s means "no sessions", not "use the
        noxfile's list" (this used to fall through to the noxfile)."""
        noxfile_config = _options.options.noxfile_namespace()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge(["-s"], noxfile_config)

        assert config.sessions == []

    def test_cli_keywords_suppress_noxfile_sessions(self) -> None:
        noxfile_config = _options.options.noxfile_namespace()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge(["-k", "test"], noxfile_config)

        assert config.sessions is None
        assert config.keywords == "test"

    def test_env_sessions_suppress_noxfile_sessions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NOXSESSION", "a,b")
        noxfile_config = _options.options.noxfile_namespace()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge([], noxfile_config)

        assert config.sessions == ["a", "b"]

    def test_noxfile_beats_ci_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CI", "1")
        noxfile_config = _options.options.noxfile_namespace()
        noxfile_config.error_on_missing_interpreters = False
        config = self.parse_and_merge([], noxfile_config)

        assert config.error_on_missing_interpreters is False

    def test_merged_defaults(self) -> None:
        config = self.parse_and_merge([], _options.options.noxfile_namespace())

        assert config.envdir == ".nox"
        assert config.reuse_venv == "no"
        assert config.default_venv_backend == "virtualenv"


class TestEnvVars:
    def test_invalid_value_is_a_clean_error(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A bad env-var value must produce a parser error, not a traceback."""
        monkeypatch.setenv("NOX_DOWNLOAD_PYTHON", "bogus")

        with pytest.raises(SystemExit):
            _options.options.parse_args([])

        assert "'download_python' must be in" in capsys.readouterr().err


class TestReuseAliasPrecedence:
    """An explicit --reuse-venv on the command line now wins over the -r/-N
    aliases given alongside it (the aliases used to win). -R still wins."""

    def test_r_with_explicit_reuse_venv(self) -> None:
        config = _options.options.parse_args(["-r", "--reuse-venv", "never"])

        assert config.reuse_venv == "never"

    def test_no_reuse_with_explicit_reuse_venv(self) -> None:
        config = _options.options.parse_args(["-N", "--reuse-venv", "always"])

        assert config.reuse_venv == "always"

    def test_R_beats_no_reuse(self) -> None:
        config = _options.options.parse_args(["-N", "-R"])

        assert config.reuse_venv == "yes"
