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

import pytest

from nox import _option_set, _options

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
