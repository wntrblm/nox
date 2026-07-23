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

import attrs
import pytest

from nox import _option_set, _options
from nox._option_set import Forward, Options, OptionsBase, Source, opt, to_argv

RESOURCES = Path(__file__).parent.joinpath("resources")


@attrs.define(kw_only=True)
class SmallConfig(OptionsBase):
    option_a: str = attrs.field(
        default="meep", metadata=opt("--option-a", group="group_a")
    )
    hidden_option: str = attrs.field(default="meep", metadata=opt(hidden=True))


def make_small_options() -> Options[SmallConfig]:
    return Options(
        SmallConfig,
        groups={"group_a": ("Group A", "The A group.")},
        description="test options",
    )


class TestOptions:
    def test_namespace(self) -> None:
        namespace = make_small_options().namespace()

        assert namespace.option_a == "meep"
        assert not hasattr(namespace, "non_existent_option")

    def test_namespace_values(self) -> None:
        namespace = make_small_options().namespace(option_a="moop")

        assert namespace.option_a == "moop"
        assert namespace.provenance("option_a") is Source.COMMAND_LINE
        assert namespace.provenance("hidden_option") is Source.DEFAULT

    def test_namespace_non_existent_options_with_values(self) -> None:
        with pytest.raises(KeyError):
            make_small_options().namespace(non_existent_option="meep")

    def test_parser_hidden_option(self) -> None:
        options = make_small_options()

        parser = options.parser()
        config = options.expand(parser.parse_args([]))

        assert config.hidden_option == "meep"
        assert "hidden_option" not in parser.format_help()

    def test_parser_groupless_option(self) -> None:
        @attrs.define(kw_only=True)
        class GrouplessConfig(OptionsBase):
            no_group: str = attrs.field(default="meep", metadata=opt("--no-group"))

        options = Options(GrouplessConfig, groups={}, description="")

        with pytest.raises(
            ValueError,
            match="Option no_group must either have a group or be hidden",
        ):
            options.parser()

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
            sessions=("baz",), keywords=None, posargs=[]
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
            default_venv_backend="virtualenv",
            download_python="auto",
            envdir=".nox",
            error_on_external_run=False,
            error_on_missing_interpreters=False,
            force_venv_backend=None,
            keywords=None,
            pythons=None,
            report=None,
            reuse_existing_virtualenvs=False,
            reuse_venv="no",
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
        # These used to accept None to mean "unset"; now they hold real values.
        with pytest.raises(ValueError):  # noqa: PT011
            options.reuse_venv = None
        with pytest.raises(TypeError):
            options.default_venv_backend = None


def _forwardable_fields() -> list[str]:
    return [
        field.name
        for field in attrs.fields(_options.NoxConfig)
        if (o := _option_set._get_opt(field)) is not None
        and o.forward is not Forward.NEVER
    ]


class TestToArgv:
    @pytest.mark.parametrize(
        "args",
        [
            [],
            ["-r"],
            ["-R"],
            ["--verbose", "--reuse-venv", "never", "--envdir", "elsewhere"],
            ["--no-verbose", "--error-on-missing-interpreters"],
            ["--forcecolor", "-s", "a", "b", "-p", "3.12", "3.13"],
            ["--nocolor", "--install-only", "--non-interactive", "-ts"],
            ["--default-venv-backend", "uv", "--download-python", "never"],
            ["--force-python", "3.13", "--stop-on-first-error"],
            ["-s", "test", "--", "-k", "foo", "--flag"],
        ],
    )
    def test_round_trip(self, args: list[str]) -> None:
        """Parsing to_argv's output must restore every forwardable value."""
        config = _options.options.parse_args(args)
        rebuilt = _options.options.parse_args(to_argv(config))

        for name in _forwardable_fields():
            assert getattr(rebuilt, name) == getattr(config, name), name

    def test_never_forwarded(self) -> None:
        config = _options.options.parse_args(
            ["--list-sessions", "--json", "--no-venv", "-R"]
        )
        argv = to_argv(config)

        for flag in ("--list-sessions", "--json", "--no-venv", "-R"):
            assert flag not in argv
        # The alias state is forwarded through the canonical options instead.
        assert "--no-install" in argv
        assert argv[argv.index("--reuse-venv") :][:2] == ["--reuse-venv", "yes"]

    def test_flag_pairs_always_emitted(self) -> None:
        """Environment-dependent pair defaults must be pinned for children."""
        argv = to_argv(_options.options.parse_args([]))

        assert (
            "--error-on-missing-interpreters" in argv
            or "--no-error-on-missing-interpreters" in argv
        )
        assert "--verbose" in argv or "--no-verbose" in argv

    def test_noxfile_only_backend_skipped(self) -> None:
        """The "a|b" fallback syntax is not valid on the CLI, so it is not
        forwarded; children re-derive it from the noxfile."""
        config = _options.options.namespace(default_venv_backend="uv|virtualenv")
        argv = to_argv(config)

        assert "--default-venv-backend" not in argv

    def test_posargs_last(self) -> None:
        config = _options.options.parse_args(["-v", "--", "posarg"])
        argv = to_argv(config)

        assert argv[-2:] == ["--", "posarg"]

    def test_evolve_selects_session(self) -> None:
        """The pattern used to spawn a child nox for a single session."""
        config = _options.options.parse_args(["-s", "a", "b", "-k", "expr"])
        child = attrs.evolve(config, sessions=["b"], keywords=None, tags=None)
        argv = to_argv(child)

        assert argv[argv.index("--session") :][:2] == ["--session", "b"]
        assert "--keywords" not in argv


class TestMerge:
    def parse_and_merge(
        self, args: list[str], noxfile_config: _options.NoxfileOptions
    ) -> _options.NoxConfig:
        config = _options.options.parse_args(args)
        _options.merge_noxfile_options(config, noxfile_config)
        return config

    def test_noxfile_beats_default(self) -> None:
        noxfile_config = _options.NoxfileOptions()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge([], noxfile_config)

        assert config.sessions == ["lint"]

    def test_cli_beats_noxfile(self) -> None:
        noxfile_config = _options.NoxfileOptions()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge(["-s", "test"], noxfile_config)

        assert config.sessions == ["test"]

    def test_cli_reuse_venv_beats_noxfile_alias(self) -> None:
        """An explicit CLI --reuse-venv wins over the noxfile's legacy
        reuse_existing_virtualenvs alias (this used to be reversed)."""
        noxfile_config = _options.NoxfileOptions()
        noxfile_config.reuse_existing_virtualenvs = True
        config = self.parse_and_merge(["--reuse-venv", "never"], noxfile_config)

        assert config.reuse_venv == "never"

    def test_bare_sessions_flag_beats_noxfile(self) -> None:
        """An explicit but empty -s means "no sessions", not "use the
        noxfile's list" (this used to fall through to the noxfile)."""
        noxfile_config = _options.NoxfileOptions()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge(["-s"], noxfile_config)

        assert config.sessions == []

    def test_cli_keywords_suppress_noxfile_sessions(self) -> None:
        noxfile_config = _options.NoxfileOptions()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge(["-k", "test"], noxfile_config)

        assert config.sessions is None
        assert config.keywords == "test"

    def test_env_sessions_suppress_noxfile_sessions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NOXSESSION", "a,b")
        noxfile_config = _options.NoxfileOptions()
        noxfile_config.sessions = ["lint"]
        config = self.parse_and_merge([], noxfile_config)

        assert config.sessions == ["a", "b"]
        assert config.provenance("sessions") is Source.ENVIRONMENT

    def test_noxfile_beats_ci_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CI", "1")
        noxfile_config = _options.NoxfileOptions()
        noxfile_config.error_on_missing_interpreters = False
        config = self.parse_and_merge([], noxfile_config)

        assert config.error_on_missing_interpreters is False

    def test_merged_defaults(self) -> None:
        config = self.parse_and_merge([], _options.NoxfileOptions())

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


class TestProvenance:
    def test_posargs_default(self) -> None:
        config = _options.options.parse_args([])

        assert config.provenance("posargs") is Source.DEFAULT

    def test_posargs_given(self) -> None:
        config = _options.options.parse_args(["--", "x"])

        assert config.provenance("posargs") is Source.COMMAND_LINE

    def test_evolve_resets_provenance(self) -> None:
        config = _options.options.parse_args(["-s", "a"])
        child = attrs.evolve(config)

        assert config.provenance("sessions") is Source.COMMAND_LINE
        assert child.provenance("sessions") is Source.DEFAULT
