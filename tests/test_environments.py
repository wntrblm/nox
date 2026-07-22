# Copyright 2026 Alethea Katherine Flowers
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

import json
import os
from typing import TYPE_CHECKING
from unittest import mock

import pytest

import nox
import nox._options
import nox.manifest
import nox.registry
import nox.sessions
import nox.tasks
from nox.environments import Environment
from nox.manifest import Manifest

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def make_manifest(**config_kwargs: object) -> Manifest:
    config = nox._options.options.namespace(posargs=[], **config_kwargs)
    return Manifest(nox.registry.get_registry(), config)


def signatures(manifest: Manifest) -> list[Sequence[str]]:
    return [session.signatures for session, _ in manifest.list_all_sessions()]


# Registration


def test_env_returns_environment() -> None:
    tooling = nox.env("tooling", python="3.12")
    assert isinstance(tooling, Environment)
    assert tooling.name == "tooling"
    assert tooling.python == "3.12"
    assert nox.registry.get_registry().envs["tooling"] is tooling


def test_env_task_decorator_plain() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    assert nox.registry.get_registry().tasks["tooling"]["lint"] is lint
    assert lint.task_name == "lint"
    assert lint.env is tooling


def test_env_task_decorator_options() -> None:
    tooling = nox.env("tooling")

    @tooling.task(name="check", tags=["a"], default=False, requires=["other"])
    def lint(session: nox.Session) -> None:
        pass

    assert nox.registry.get_registry().tasks["tooling"]["check"] is lint
    assert lint.tags == ["a"]
    assert lint.default is False
    assert lint.requires == ["other"]


def test_duplicate_env_error() -> None:
    nox.env("tooling")
    with pytest.raises(ValueError, match="already registered"):
        nox.env("tooling")


def test_duplicate_task_error() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    with pytest.raises(ValueError, match="already registered"):

        @tooling.task(name="lint")
        def lint2(session: nox.Session) -> None:
            pass


@pytest.mark.parametrize("name", ["", "a:b", "a(b"])
def test_invalid_names(name: str) -> None:
    with pytest.raises(ValueError, match="name"):
        nox.env(name)


def test_invalid_task_name() -> None:
    tooling = nox.env("tooling")
    with pytest.raises(ValueError, match="task name"):

        @tooling.task(name="a:b")
        def lint(session: nox.Session) -> None:
            pass


def test_task_shared_across_envs() -> None:
    env_a = nox.env("a")
    env_b = nox.env("b")

    @env_b.task
    @env_a.task
    def check(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    assert "a:check" in manifest
    assert "b:check" in manifest


def test_task_requires_registered_env() -> None:
    env = Environment("ghost", register=False)

    with pytest.raises(ValueError, match="not registered"):

        @env.task
        def check(session: nox.Session) -> None:
            pass


def test_alias_registration() -> None:
    nox.alias("check", "tooling:lint", "tooling:typecheck")
    assert nox.registry.get_registry().aliases["check"] == (
        "tooling:lint",
        "tooling:typecheck",
    )


def test_alias_requires_targets() -> None:
    with pytest.raises(ValueError, match="at least one target"):
        nox.alias("check")


def test_alias_env_collision() -> None:
    nox.env("tooling")
    with pytest.raises(ValueError, match="already registered"):
        nox.alias("tooling", "a:b")
    nox.alias("check", "a:b")
    with pytest.raises(ValueError, match="already registered"):
        nox.env("check")


def test_session_env_collision() -> None:
    nox.env("tooling")
    with pytest.raises(ValueError, match="share one namespace"):

        @nox.session(name="tooling")
        def tooling(session: nox.Session) -> None:
            pass


def test_session_alias_collision() -> None:
    nox.alias("check", "a:b")
    with pytest.raises(ValueError, match="share one namespace"):

        @nox.session(name="check")
        def check(session: nox.Session) -> None:
            pass


# Manifest construction


def test_task_signatures_no_python() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    session = manifest["tooling:lint"]
    assert session.signatures == ["tooling:lint"]
    assert session.name == "tooling:lint"
    assert session.task_name == "lint"
    assert session.env_base_name == "tooling"
    assert session.env_instance_name == "tooling"
    assert session.friendly_name == "tooling:lint"


def test_task_signatures_single_python() -> None:
    tooling = nox.env("tooling", python="3.12")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    session = manifest["tooling:lint"]
    assert session.signatures == ["tooling:lint", "tooling-3.12:lint"]
    assert session.func.python == "3.12"


def test_task_signatures_python_matrix() -> None:
    tests = nox.env("tests", python=["3.11", "3.12"])

    @tests.task
    def run(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    assert signatures(manifest) == [["tests-3.11:run"], ["tests-3.12:run"]]
    session = manifest["tests-3.11:run"]
    assert session.multi
    assert session.env_instance_name == "tests-3.11"
    assert session.env_base_name == "tests"


def test_task_parametrize() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    @nox.parametrize("x", [1, 2])
    def lint(session: nox.Session, x: int) -> None:
        pass

    manifest = make_manifest()
    assert signatures(manifest) == [["tooling:lint(x=1)"], ["tooling:lint(x=2)"]]
    # Both parametrizations share the environment's venv.
    runners = [session for session, _ in manifest.list_all_sessions()]
    assert runners[0].env_runner is runners[1].env_runner


def test_matrix_parametrized_task() -> None:
    env = nox.env("tests", python=["3.11", "3.12"])

    @env.task
    @nox.parametrize("x", [1, 2])
    def run(session: nox.Session, x: int) -> None:
        pass

    manifest = make_manifest()
    assert signatures(manifest) == [
        ["tests-3.11:run(x=1)", "tests-3.11:run"],
        ["tests-3.11:run(x=2)", "tests-3.11:run"],
        ["tests-3.12:run(x=1)", "tests-3.12:run"],
        ["tests-3.12:run(x=2)", "tests-3.12:run"],
    ]
    # The instance task id runs every parametrization of that instance.
    manifest.filter_by_name(["tests-3.11:run"])
    assert [session.friendly_name for session in manifest._queue] == [
        "tests-3.11:run(x=1)",
        "tests-3.11:run(x=2)",
    ]


def test_env_python_list_no_venv_warns() -> None:
    env = nox.env("tests", python=["3.11", "3.12"], venv_backend="none")

    @env.task
    def run(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    runner = manifest["tests:run"]
    assert runner.func.python is False
    assert nox.manifest.WARN_PYTHONS_IGNORED in runner.func.should_warn


def test_env_extra_pythons() -> None:
    tests = nox.env("tests", python=["3.11"])

    @tests.task
    def run(session: nox.Session) -> None:
        pass

    tools = nox.env("tools")

    @tools.task
    def lint(session: nox.Session) -> None:
        pass

    manifest = make_manifest(extra_pythons=["3.12"])
    names = [session.friendly_name for session, _ in manifest.list_all_sessions()]
    assert names == ["tests-3.11:run", "tests-3.12:run", "tools:lint"]


def test_task_parametrize_python_forbidden() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    @nox.parametrize("python", ["3.11", "3.12"])
    def lint(session: nox.Session) -> None:
        pass

    with pytest.raises(ValueError, match="cannot parametrize 'python'"):
        make_manifest()


def test_tasks_share_env_runner_and_envdir() -> None:
    tooling = nox.env("tooling", python="3.12", tags=["env-tag"])

    @tooling.task(tags=["task-tag"])
    def lint(session: nox.Session) -> None:
        pass

    @tooling.task
    def typecheck(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox")
    lint_runner = manifest["tooling:lint"]
    typecheck_runner = manifest["tooling:typecheck"]
    assert lint_runner.env_runner is typecheck_runner.env_runner
    assert lint_runner.envdir == os.path.join(".nox", "tooling")
    assert lint_runner.tags == ["env-tag", "task-tag"]
    assert typecheck_runner.tags == ["env-tag"]


def test_python_matrix_envdir_per_instance() -> None:
    tests = nox.env("tests", python=["3.11", "3.12"])

    @tests.task
    def run(session: nox.Session) -> None:
        pass

    @tests.task
    def cov(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox")
    assert manifest["tests-3.11:run"].envdir == os.path.join(".nox", "tests-3-11")
    assert (
        manifest["tests-3.11:run"].env_runner is manifest["tests-3.11:cov"].env_runner
    )
    assert (
        manifest["tests-3.11:run"].env_runner
        is not manifest["tests-3.12:run"].env_runner
    )


def test_session_and_env_coexist() -> None:
    @nox.session(venv_backend="none")
    def lint(session: nox.Session) -> None:
        pass

    tests = nox.env("tests")

    @tests.task
    def run(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    assert signatures(manifest) == [["lint"], ["tests:run"]]


# Selection


def make_selection_envs() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    @tooling.task(default=False)
    def typecheck(session: nox.Session) -> None:
        pass

    docs = nox.env("docs")

    @docs.task
    def build(session: nox.Session) -> None:
        pass

    @docs.task(name="lint")
    def docs_lint(session: nox.Session) -> None:
        pass


def selected(manifest: Manifest) -> list[str]:
    return [
        session.friendly_name for session, sel in manifest.list_all_sessions() if sel
    ]


def test_filter_by_canonical_name() -> None:
    make_selection_envs()
    manifest = make_manifest()
    manifest.filter_by_name(["tooling:lint"])
    assert selected(manifest) == ["tooling:lint"]


def test_filter_by_env_name_selects_default_tasks() -> None:
    make_selection_envs()
    manifest = make_manifest()
    manifest.filter_by_name(["tooling"])
    # typecheck is default=False, so the env selector skips it.
    assert selected(manifest) == ["tooling:lint"]


def test_filter_by_unique_task_name() -> None:
    make_selection_envs()
    manifest = make_manifest()
    manifest.filter_by_name(["build"])
    assert selected(manifest) == ["docs:build"]


def test_filter_by_ambiguous_task_name() -> None:
    make_selection_envs()
    manifest = make_manifest()
    with pytest.raises(ValueError, match=r"ambiguous.*docs:lint.*tooling:lint"):
        manifest.filter_by_name(["lint"])


def test_filter_by_alias() -> None:
    make_selection_envs()
    nox.alias("check", "tooling:lint", "docs:build")
    manifest = make_manifest()
    manifest.filter_by_name(["check"])
    assert selected(manifest) == ["tooling:lint", "docs:build"]


def test_filter_by_env_instance_name() -> None:
    tests = nox.env("tests", python=["3.11", "3.12"])

    @tests.task
    def run(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    manifest.filter_by_name(["tests-3.11"])
    assert selected(manifest) == ["tests-3.11:run"]


def test_filter_by_normalized_matrix_id() -> None:
    env = nox.env("tests", python=["3.11", "3.12"])

    @env.task
    def run(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    # Formatting variants of the canonical id still match every instance.
    manifest.filter_by_name(["tests:run "])
    assert [session.friendly_name for session in manifest._queue] == [
        "tests-3.11:run",
        "tests-3.12:run",
    ]


def test_filter_missing_name() -> None:
    make_selection_envs()
    manifest = make_manifest()
    with pytest.raises(KeyError, match="nonsense"):
        manifest.filter_by_name(["nonsense"])


def test_filter_by_keywords_env_name() -> None:
    make_selection_envs()
    manifest = make_manifest()
    manifest.filter_by_keywords("tooling")
    assert len(manifest) == 2


# Dependencies


def test_requires_canonical_id() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    other = nox.env("other")

    @other.task(requires=["tooling:lint"])
    def check(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    manifest.filter_by_name(["other:check"])
    manifest.add_dependencies()
    assert [session.friendly_name for session in manifest._queue] == [
        "tooling:lint",
        "other:check",
    ]


def test_requires_alias_and_bare_task() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    @tooling.task
    def typecheck(session: nox.Session) -> None:
        pass

    nox.alias("check", "tooling:lint", "tooling:typecheck")

    other = nox.env("other")

    @other.task(requires=["check"])
    def via_alias(session: nox.Session) -> None:
        pass

    @other.task(requires=["typecheck"])
    def via_task(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    manifest.filter_by_name(["other:via_alias", "other:via_task"])
    manifest.add_dependencies()
    assert [session.friendly_name for session in manifest._queue] == [
        "tooling:lint",
        "tooling:typecheck",
        "other:via_alias",
        "other:via_task",
    ]


def test_requires_env_name_single_task() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    other = nox.env("other")

    @other.task(requires=["tooling"])
    def check(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    manifest.filter_by_name(["other:check"])
    manifest.add_dependencies()
    assert [session.friendly_name for session in manifest._queue] == [
        "tooling:lint",
        "other:check",
    ]


def test_requires_env_name_multiple_tasks_selects_defaults() -> None:
    make_selection_envs()

    other = nox.env("other")

    @other.task(requires=["tooling"])
    def check(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    manifest.filter_by_name(["other:check"])
    manifest.add_dependencies()
    # typecheck is default=False, so only the default task is pulled in.
    assert [session.friendly_name for session in manifest._queue] == [
        "tooling:lint",
        "other:check",
    ]


def test_requires_matrix_task() -> None:
    tests = nox.env("tests", python=["3.11", "3.12"])

    @tests.task
    def run(session: nox.Session) -> None:
        pass

    other = nox.env("other")

    @other.task(requires=["tests:run"])
    def check(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    manifest.filter_by_name(["other:check"])
    manifest.add_dependencies()
    assert [session.friendly_name for session in manifest._queue] == [
        "tests-3.11:run",
        "tests-3.12:run",
        "other:check",
    ]


def test_bare_task_requires_prefers_real_session() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    @nox.session(name="lint")
    def lint_session(session: nox.Session) -> None:
        pass

    other = nox.env("other")

    @other.task(requires=["lint"])
    def check(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    manifest.filter_by_name(["other:check"])
    manifest.add_dependencies()
    # The real session named "lint" wins over the bare-task shorthand for
    # tooling:lint.
    assert [session.friendly_name for session in manifest._queue] == [
        "lint",
        "other:check",
    ]


def test_extra_requirements_skip_non_default_envs() -> None:
    env = nox.env("tests", python=["3.11", "3.12"])

    @env.task(default=False)
    def run(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    extra = manifest._extra_requirements()
    # Env and instance selectors with no default tasks are not requirable...
    assert "tests" not in extra
    assert "tests-3.11" not in extra
    # ...but the unique bare task name still is.
    assert extra["run"] == ["tests:run"]


# Notify


def test_notify_env_selector_with_posargs() -> None:
    make_selection_envs()
    manifest = make_manifest()
    manifest.filter_by_name(["docs:build"])
    assert manifest.notify("tooling", posargs=["-x"])
    assert manifest["tooling:lint"].posargs == ["-x"]


def test_notify_unknown_runner_object() -> None:
    make_selection_envs()
    manifest = make_manifest()
    foreign = nox.sessions.SessionRunner(
        "ghost",
        [],
        nox.manifest._null_session_func,
        manifest._config,
        manifest,
        multi=False,
    )
    with pytest.raises(ValueError, match="not found"):
        manifest.notify(foreign)


# Execution


def run_manifest_sessions(manifest: Manifest) -> list[nox.sessions.Result]:
    return [session.execute() for session in manifest]


def test_shared_env_created_once() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    @tooling.task
    def typecheck(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox", noxfile="noxfile.py")

    fake_venv = mock.MagicMock()
    fake_venv.env = {}
    fake_venv._reused = False
    with mock.patch(
        "nox.sessions.get_virtualenv", return_value=fake_venv
    ) as get_virtualenv:
        results = run_manifest_sessions(manifest)

    assert all(results)
    assert get_virtualenv.call_count == 1
    assert fake_venv.create.call_count == 1


def test_shared_env_failure_propagates() -> None:
    tooling = nox.env("tooling", python="9.99")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    @tooling.task
    def typecheck(session: nox.Session) -> None:
        pass

    manifest = make_manifest(
        envdir=".nox", noxfile="noxfile.py", error_on_missing_interpreters=True
    )

    with mock.patch(
        "nox.sessions.get_virtualenv",
        side_effect=nox.virtualenv.InterpreterNotFound("9.99"),
    ) as get_virtualenv:
        results = run_manifest_sessions(manifest)

    assert not any(results)
    # The second task fails fast from the cached error, without retrying.
    assert get_virtualenv.call_count == 1


def test_shared_env_keyboard_interrupt_not_cached() -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox", noxfile="noxfile.py")
    runner = manifest["tooling:lint"].env_runner
    with (
        mock.patch.object(runner, "_create_venv", side_effect=KeyboardInterrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        runner.ensure()
    assert runner._error is None


def test_requires_failure_aborts_dependent() -> None:
    tooling = nox.env("tooling", venv_backend="none")

    @tooling.task
    def lint(session: nox.Session) -> None:
        session.error("boom")

    other = nox.env("other", venv_backend="none")

    @other.task(requires=["tooling:lint"])
    def check(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox", noxfile="noxfile.py")
    manifest.filter_by_name(["other:check"])
    manifest.add_dependencies()
    results = run_manifest_sessions(manifest)
    assert [result.status for result in results] == [
        nox.sessions.Status.ABORTED,
        nox.sessions.Status.ABORTED,
    ]
    assert "was not successful" in (results[1].reason or "")


# Provisioning


def test_base_sync_installs_dependencies() -> None:
    env = nox.env("dev", dependencies=["requests", "rich"])
    session = mock.MagicMock()
    env.sync(session)
    session.install.assert_called_once_with("requests", "rich")


class TrackingEnvironment(Environment):
    """Records sync/setup calls instead of installing."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.sync_calls = 0

    def sync(self, session: nox.Session) -> None:  # noqa: ARG002
        self.sync_calls += 1


def make_provision_env(
    tmp_path: Path, dependencies: Sequence[str] = ("requests",)
) -> TrackingEnvironment:
    env = TrackingEnvironment("dev", dependencies=list(dependencies))

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    (tmp_path / ".nox" / "dev").mkdir(parents=True, exist_ok=True)
    return env


def execute_provision(tmp_path: Path, *, reused: bool, **config_kwargs: object) -> None:
    config = nox._options.options.namespace(
        posargs=[],
        envdir=str(tmp_path / ".nox"),
        noxfile=str(tmp_path / "noxfile.py"),
        **config_kwargs,
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    fake_venv = mock.MagicMock()
    fake_venv.env = {}
    fake_venv._reused = reused
    fake_venv.venv_backend = "uv"
    with mock.patch("nox.sessions.get_virtualenv", return_value=fake_venv):
        for session in manifest:
            assert session.execute()


def test_provision_writes_stamp(tmp_path: Path) -> None:
    env = make_provision_env(tmp_path)
    execute_provision(tmp_path, reused=False)
    assert env.sync_calls == 1
    stamp = json.loads(
        (tmp_path / ".nox" / "dev" / ".nox-env.json").read_text(encoding="utf-8")
    )
    assert stamp["env"]["dependencies"] == ["requests"]


def test_provision_skips_when_stamp_matches(tmp_path: Path) -> None:
    env = make_provision_env(tmp_path)
    execute_provision(tmp_path, reused=False)
    assert env.sync_calls == 1

    nox.registry.reset()
    env2 = make_provision_env(tmp_path)
    execute_provision(tmp_path, reused=True)
    assert env2.sync_calls == 0


def test_provision_resyncs_on_change(tmp_path: Path) -> None:
    make_provision_env(tmp_path)
    execute_provision(tmp_path, reused=False)

    nox.registry.reset()
    env2 = make_provision_env(tmp_path, dependencies=["requests", "rich"])
    execute_provision(tmp_path, reused=True)
    assert env2.sync_calls == 1
    stamp = json.loads(
        (tmp_path / ".nox" / "dev" / ".nox-env.json").read_text(encoding="utf-8")
    )
    assert stamp["env"]["dependencies"] == ["requests", "rich"]


def test_provision_syncs_fresh_venv_even_with_stamp(tmp_path: Path) -> None:
    make_provision_env(tmp_path)
    execute_provision(tmp_path, reused=False)

    nox.registry.reset()
    env2 = make_provision_env(tmp_path)
    execute_provision(tmp_path, reused=False)
    assert env2.sync_calls == 1


def test_provision_no_install_skips(tmp_path: Path) -> None:
    env = make_provision_env(tmp_path)
    execute_provision(tmp_path, reused=True, no_install=True)
    assert env.sync_calls == 0


def test_provision_corrupt_stamp_resyncs(tmp_path: Path) -> None:
    env = make_provision_env(tmp_path)
    stamp_path = tmp_path / ".nox" / "dev" / ".nox-env.json"
    stamp_path.write_text("{corrupt", encoding="utf-8")
    execute_provision(tmp_path, reused=True)
    assert env.sync_calls == 1


def test_provision_failure_cached(tmp_path: Path) -> None:
    class FailingEnvironment(TrackingEnvironment):
        def sync(self, session: nox.Session) -> None:
            super().sync(session)
            msg = "sync failed"
            raise RuntimeError(msg)

    env = FailingEnvironment("dev", dependencies=["requests"])

    @env.task
    def a(session: nox.Session) -> None:
        pass

    @env.task
    def b(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[],
        envdir=str(tmp_path / ".nox"),
        noxfile=str(tmp_path / "noxfile.py"),
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    fake_venv = mock.MagicMock()
    fake_venv.env = {}
    fake_venv._reused = False
    fake_venv.venv_backend = "uv"
    with mock.patch("nox.sessions.get_virtualenv", return_value=fake_venv):
        results = [session.execute() for session in manifest]

    assert not any(results)
    # The second task fails fast from the cached error, without re-syncing.
    assert env.sync_calls == 1
    with pytest.raises(RuntimeError, match="sync failed"):
        manifest["dev:a"].env_runner.provision(mock.MagicMock())


def test_provision_keyboard_interrupt_not_cached(tmp_path: Path) -> None:
    make_provision_env(tmp_path)
    config = nox._options.options.namespace(
        posargs=[],
        envdir=str(tmp_path / ".nox"),
        noxfile=str(tmp_path / "noxfile.py"),
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    runner = manifest["dev:sync"].env_runner
    with (
        mock.patch.object(runner, "_provision", side_effect=KeyboardInterrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        runner.provision(mock.MagicMock())
    assert runner._error is None


def test_setup_hook_unstampable(tmp_path: Path) -> None:
    env = make_provision_env(tmp_path)
    setup_calls = []

    @env.setup
    def _(session: nox.Session) -> None:
        setup_calls.append(session)

    assert env.stamp_data() is None
    execute_provision(tmp_path, reused=True)
    assert env.sync_calls == 1
    assert len(setup_calls) == 1
    assert not (tmp_path / ".nox" / "dev" / ".nox-env.json").exists()


def test_setup_stamp_makes_stampable(tmp_path: Path) -> None:
    env = make_provision_env(tmp_path)
    env.setup_stamp = "v1"

    @env.setup
    def _(session: nox.Session) -> None:
        pass

    data = env.stamp_data()
    assert data is not None
    assert data["setup_stamp"] == "v1"


def test_setup_hook_only_once() -> None:
    env = nox.env("dev")

    @env.setup
    def _(session: nox.Session) -> None:
        pass

    with pytest.raises(ValueError, match="already has a setup function"):

        @env.setup
        def _(session: nox.Session) -> None:
            pass


# Locations


def test_location_envdir(tmp_path: Path) -> None:
    env = nox.env("dev", location=".venv")

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[], envdir=".nox", noxfile=str(tmp_path / "noxfile.py")
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    assert manifest["dev:sync"].envdir == os.path.join(
        os.path.realpath(tmp_path), ".venv"
    )


def test_location_matrix_requires_placeholder() -> None:
    env = nox.env("tests", python=["3.11", "3.12"], location=".venv")

    @env.task
    def run(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox")
    with pytest.raises(ValueError, match="placeholder"):
        manifest.check_location_collisions()


def test_location_matrix_placeholder(tmp_path: Path) -> None:
    env = nox.env("tests", python=["3.11", "3.12"], location=".venvs/{name}")

    @env.task
    def run(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[], envdir=".nox", noxfile=str(tmp_path / "noxfile.py")
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    assert manifest["tests-3.11:run"].envdir == os.path.join(
        os.path.realpath(tmp_path), ".venvs", "tests-3.11"
    )


def test_location_duplicate_error() -> None:
    env_a = nox.env("a", location=".venv")
    env_b = nox.env("b", location=".venv")

    @env_a.task
    def sync(session: nox.Session) -> None:
        pass

    @env_b.task(name="sync")
    def sync_b(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox")
    with pytest.raises(ValueError, match="both resolve to the location"):
        manifest.check_location_collisions()


def test_location_shared_template_ok(tmp_path: Path) -> None:
    env_a = nox.env("a", python=["3.11", "3.12"], location=".venvs/{name}")
    env_b = nox.env("b", python=["3.11", "3.12"], location=".venvs/{name}")

    @env_a.task
    def run(session: nox.Session) -> None:
        pass

    @env_b.task(name="run")
    def run_b(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[], envdir=".nox", noxfile=str(tmp_path / "noxfile.py")
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    assert manifest["a-3.11:run"].envdir != manifest["b-3.11:run"].envdir


def test_location_template_collision_error(tmp_path: Path) -> None:
    env_a = nox.env("a", python="3.12", location=".venvs/{python}")
    env_b = nox.env("b", python="3.12", location=".venvs/{python}")

    @env_a.task
    def run(session: nox.Session) -> None:
        pass

    @env_b.task(name="run")
    def run_b(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[], envdir=".nox", noxfile=str(tmp_path / "noxfile.py")
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    with pytest.raises(ValueError, match="both resolve to the location"):
        manifest.check_location_collisions()


def test_location_ownership_guard(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "precious.txt").write_text("data", encoding="utf-8")
    env = nox.env("dev", location=".venv")

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[], envdir=".nox", noxfile=str(tmp_path / "noxfile.py")
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    with pytest.raises(OSError, match="Refusing to use"):
        manifest["dev:sync"].env_runner._check_location_ownership()
    assert (tmp_path / ".venv" / "precious.txt").exists()


def test_location_ownership_venv_ok(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pyvenv.cfg").write_text(
        "home = /usr/bin\n", encoding="utf-8"
    )
    env = nox.env("dev", location=".venv")

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[], envdir=".nox", noxfile=str(tmp_path / "noxfile.py")
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    manifest["dev:sync"].env_runner._check_location_ownership()


def test_located_env_create_checks_ownership(tmp_path: Path) -> None:
    env = nox.env("dev", location=".venv")

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[], envdir=".nox", noxfile=str(tmp_path / "noxfile.py")
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    fake_venv = mock.MagicMock()
    fake_venv.env = {}
    fake_venv._reused = False
    with mock.patch(
        "nox.sessions.get_virtualenv", return_value=fake_venv
    ) as get_virtualenv:
        manifest["dev:sync"].env_runner.ensure()
    # Located envs never get .gitignore/CACHEDIR.TAG dropped next to them.
    assert get_virtualenv.call_args.kwargs["manage_parent_dir"] is False


def test_location_ownership_conda_ok(tmp_path: Path) -> None:
    (tmp_path / ".venv" / "conda-meta").mkdir(parents=True)
    env = nox.env("dev", location=".venv")

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[], envdir=".nox", noxfile=str(tmp_path / "noxfile.py")
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    manifest["dev:sync"].env_runner._check_location_ownership()


def test_filter_manifest_location_collision(tmp_path: Path) -> None:
    env_a = nox.env("a", location=".venv")

    @env_a.task
    def sync_a(session: nox.Session) -> None:
        pass

    env_b = nox.env("b", location=".venv")

    @env_b.task
    def sync_b(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[], envdir=".nox", noxfile=str(tmp_path / "noxfile.py")
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    assert nox.tasks.filter_manifest(manifest, config) == 3


# Lock file environment types


def test_env_namespace_types() -> None:
    assert nox.env.pylock is nox.environments.PylockEnvironment
    assert nox.env.uv is nox.environments.UvProjectEnvironment


def test_pylock_stamp(tmp_path: Path) -> None:
    lockfile = tmp_path / "pylock.toml"
    lockfile.write_text("lock-version = '1.0'\n", encoding="utf-8")
    env = nox.env.pylock("ci", lockfile=lockfile)
    data = env.stamp_data()
    assert data is not None
    assert data["kind"] == "pylock"
    assert data["lockfile_hash"]

    lockfile.write_text("lock-version = '1.1'\n", encoding="utf-8")
    assert env.stamp_data() != data


def test_pylock_unstampable_setup(tmp_path: Path) -> None:
    env = nox.env.pylock("ci", lockfile=tmp_path / "pylock.toml")

    @env.setup
    def _(session: nox.Session) -> None:
        pass

    assert env.stamp_data() is None


def test_pylock_sync_is_exact() -> None:
    assert nox.env.pylock("ci").sync_is_exact
    assert not nox.env.pylock("ci2", dependencies=["pip"]).sync_is_exact


def test_pylock_sync_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox.virtualenv, "HAS_UV", True)
    monkeypatch.setattr(nox.virtualenv, "UV", "/fake/uv")
    env = nox.env.pylock("ci", lockfile="pylock.toml")
    session = mock.MagicMock()
    session.venv_backend = "uv"
    session.virtualenv.is_sandboxed = True
    env.sync(session)
    session.run_install.assert_called_once_with(
        "/fake/uv", "pip", "sync", "pylock.toml", external=True, silent=True
    )


def test_pylock_sync_requires_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox.virtualenv, "HAS_UV", False)
    env = nox.env.pylock("ci")
    with pytest.raises(RuntimeError, match="requires uv"):
        env.sync(mock.MagicMock())


def test_pylock_sync_requires_venv_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nox.virtualenv, "HAS_UV", True)
    env = nox.env.pylock("ci")
    session = mock.MagicMock()
    session.venv_backend = "conda"
    session.virtualenv.is_sandboxed = True
    with pytest.raises(RuntimeError, match="virtualenv-style backend"):
        env.sync(session)


def test_uv_env_sync_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nox.virtualenv, "UV", "/fake/uv")
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("version = 1\n", encoding="utf-8")
    env = nox.env.uv(
        "dev",
        lockfile=lockfile,
        groups=["dev"],
        extras=["cli"],
        no_default_groups=True,
    )
    command = env._sync_command()
    assert command == [
        "sync",
        "--locked",
        f"--project={tmp_path}",
        "--group=dev",
        "--extra=cli",
        "--no-default-groups",
    ]
    data = env.stamp_data()
    assert data is not None
    assert data["kind"] == "uv"
    assert data["command"] == command

    session = mock.MagicMock()
    session.venv_backend = "uv"
    env.sync(session)
    session.run_install.assert_called_once_with(
        "/fake/uv", *command, external=True, silent=True
    )


def test_uv_env_sync_command_flags(tmp_path: Path) -> None:
    env = nox.env.uv(
        "dev",
        lockfile=tmp_path / "uv.lock",
        all_extras=True,
        no_install_project=True,
        sync_args=["--quiet"],
    )
    assert env._sync_command() == [
        "sync",
        "--locked",
        f"--project={tmp_path}",
        "--all-extras",
        "--no-install-project",
        "--quiet",
    ]


def test_uv_env_unstampable_setup(tmp_path: Path) -> None:
    env = nox.env.uv("dev", lockfile=tmp_path / "uv.lock")

    @env.setup
    def _(session: nox.Session) -> None:
        pass

    assert env.stamp_data() is None


def test_uv_env_sync_is_exact() -> None:
    assert nox.env.uv("dev").sync_is_exact
    assert not nox.env.uv("dev2", dependencies=["pip"]).sync_is_exact


def test_uv_env_backend_forced() -> None:
    assert nox.env.uv("dev").venv_backend == "uv"
    with pytest.raises(ValueError, match="requires the 'uv' venv backend"):
        nox.env.uv("dev2", venv_backend="virtualenv")


def test_uv_env_missing_lockfile(tmp_path: Path) -> None:
    env = nox.env.uv("dev", lockfile=tmp_path / "uv.lock")
    with pytest.raises(FileNotFoundError, match="does not exist"):
        env.stamp_data()


# Reuse default


def test_declarative_env_reuse_default() -> None:
    env = nox.env("dev")

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox", reuse_venv=None)
    runner = manifest["dev:sync"]
    assert runner.func.reuse_venv is True
    assert runner.reuse_existing_venv()


def test_declarative_env_reuse_opt_out() -> None:
    env = nox.env("dev", reuse_venv=False)

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox", reuse_venv=None)
    assert not manifest["dev:sync"].reuse_existing_venv()


def test_legacy_session_reuse_unchanged() -> None:
    @nox.session
    def tests(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox", reuse_venv=None)
    assert not manifest["tests"].reuse_existing_venv()


# Shared install warning


def test_shared_env_install_warns_once(caplog: pytest.LogCaptureFixture) -> None:
    env = nox.env("tooling")

    @env.task
    def lint(session: nox.Session) -> None:
        pass

    @env.task
    def typecheck(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox", no_install=False, verbose=False)
    runner = manifest["tooling:lint"]
    runner.venv = mock.create_autospec(nox.virtualenv.VirtualEnv, instance=True)
    runner.venv._reused = False
    runner.venv.venv_backend = "virtualenv"  # type: ignore[misc]
    session = nox.sessions.Session(runner)
    with mock.patch.object(nox.sessions.Session, "_run"):
        session.install("requests")
        session.install("rich")
    warnings_ = [r for r in caplog.records if "shared environment" in r.message]
    assert len(warnings_) == 1


def test_own_env_install_no_warning(caplog: pytest.LogCaptureFixture) -> None:
    env = nox.env("solo")

    @env.task
    def lint(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox", no_install=False, verbose=False)
    runner = manifest["solo:lint"]
    runner.venv = mock.create_autospec(nox.virtualenv.VirtualEnv, instance=True)
    runner.venv._reused = False
    runner.venv.venv_backend = "virtualenv"  # type: ignore[misc]
    session = nox.sessions.Session(runner)
    with mock.patch.object(nox.sessions.Session, "_run"):
        session.install("requests")
    assert not [r for r in caplog.records if "shared environment" in r.message]


def test_provision_install_only_writes_stamp(tmp_path: Path) -> None:
    make_provision_env(tmp_path)
    execute_provision(tmp_path, reused=False, install_only=True)
    assert (tmp_path / ".nox" / "dev" / ".nox-env.json").exists()

    # The prepared environment is treated as up to date on the next run.
    nox.registry.reset()
    env2 = make_provision_env(tmp_path)
    execute_provision(tmp_path, reused=True)
    assert env2.sync_calls == 0


def test_provision_install_only_setup_hook_no_stamp(tmp_path: Path) -> None:
    env = make_provision_env(tmp_path)
    env.setup_stamp = "v1"

    @env.setup
    def _(session: nox.Session) -> None:
        pass

    execute_provision(tmp_path, reused=False, install_only=True)
    assert not (tmp_path / ".nox" / "dev" / ".nox-env.json").exists()


def test_filter_manifest_ambiguous_task_returns_error_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    make_selection_envs()
    config = nox._options.options.namespace(
        posargs=[], sessions=["lint"], pythons=(), keywords=(), tags=None
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    return_value = nox.tasks.filter_manifest(manifest, config)
    assert return_value == 3
    assert any("ambiguous" in record.message for record in caplog.records)


# Adversarial-review regressions


def test_legacy_session_name_with_colon_still_works() -> None:
    with pytest.warns(FutureWarning, match="contains characters"):

        @nox.session(name="docs:build", venv_backend="none")
        def docs_build(session: nox.Session) -> None:
            pass

    manifest = make_manifest()
    manifest.filter_by_name(["docs:build"])
    assert selected(manifest) == ["docs:build"]


def test_env_selector_no_default_tasks_errors() -> None:
    tooling = nox.env("tooling")

    @tooling.task(default=False)
    def lint(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    with pytest.raises(ValueError, match="has no default tasks"):
        manifest.filter_by_name(["tooling"])

    config = nox._options.options.namespace(
        posargs=[], sessions=["tooling"], pythons=(), keywords=(), tags=None
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    assert nox.tasks.filter_manifest(manifest, config) == 3


def test_alias_shadowing_task_warns(caplog: pytest.LogCaptureFixture) -> None:
    tooling = nox.env("tooling")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    nox.alias("lint", "tooling:style")
    make_manifest()
    assert any(
        "shadows the task" in record.message and "tooling:lint" in record.message
        for record in caplog.records
    )


def test_empty_parametrize_does_not_poison_env() -> None:
    tooling = nox.env("tooling", python="3.12")

    @tooling.task
    @nox.parametrize("x", [])
    def empty(session: nox.Session, x: int) -> None:
        pass

    @tooling.task
    def real(session: nox.Session) -> None:
        pass

    manifest = make_manifest()
    runner = manifest["tooling:real"]
    assert runner.env_runner is manifest["tooling:empty"].env_runner
    # The environment's venv configuration comes from the environment, not
    # from the placeholder session created for the empty parametrize list.
    assert runner.env_runner.func.python == "3.12"


def test_alias_of_alias_selection() -> None:
    make_selection_envs()
    nox.alias("style", "tooling:lint")
    nox.alias("all-checks", "style", "docs:build")
    manifest = make_manifest()
    manifest.filter_by_name(["all-checks"])
    assert selected(manifest) == ["tooling:lint", "docs:build"]


def test_alias_cycle_reports_missing() -> None:
    nox.alias("a", "b")
    nox.alias("b", "a")
    make_selection_envs()
    manifest = make_manifest()
    with pytest.raises(KeyError, match="a"):
        manifest.filter_by_name(["a"])


def test_notify_new_identifier_forms() -> None:
    make_selection_envs()
    nox.alias("style", "tooling:lint")
    manifest = make_manifest()
    manifest.filter_by_name(["docs:build"])

    assert manifest.notify("style")
    assert manifest["tooling:lint"] in manifest._queue

    assert manifest.notify("build") is False  # already selected

    # Env selector: tooling's only default task is already queued.
    assert manifest.notify("tooling") is False

    assert manifest.notify("typecheck")  # bare task name, unique

    with pytest.raises(ValueError, match="not found"):
        manifest.notify("nonsense")


def test_single_python_env_instance_selector() -> None:
    tooling = nox.env("tooling", python="3.12")

    @tooling.task
    def lint(session: nox.Session) -> None:
        pass

    other = nox.env("other", venv_backend="none")

    @other.task(requires=["tooling-3.12"])
    def check(session: nox.Session) -> None:
        pass

    manifest = make_manifest(envdir=".nox")
    manifest.filter_by_name(["tooling-3.12"])
    assert selected(manifest) == ["tooling:lint"]
    # The environment directory keeps the unsuffixed name, like classic
    # single-python sessions.
    assert manifest["tooling:lint"].envdir == os.path.join(".nox", "tooling")

    manifest = make_manifest(envdir=".nox")
    manifest.filter_by_name(["other:check"])
    manifest.add_dependencies()
    assert [session.friendly_name for session in manifest._queue] == [
        "tooling:lint",
        "other:check",
    ]


def test_discover_manifest_reports_construction_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tooling = nox.env("tooling")

    @tooling.task
    @nox.parametrize("python", ["3.11", "3.12"])
    def lint(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(posargs=[])
    module = mock.Mock(__doc__=None)
    assert nox.tasks.discover_manifest(module, config) == 3
    assert any("cannot parametrize" in record.message for record in caplog.records)


def test_uv_env_sync_refuses_other_backends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nox.virtualenv, "UV", "/fake/uv")
    env = nox.env.uv("dev")
    session = mock.MagicMock()
    session.venv_backend = "virtualenv"
    with pytest.raises(RuntimeError, match="must run on the 'uv' venv backend"):
        env.sync(session)
    session.run_install.assert_not_called()


def test_forced_python_on_located_env_does_not_break_others(
    tmp_path: Path,
) -> None:
    dev = nox.env("dev", python="3.12", location=".devenv")

    @dev.task
    def sync(session: nox.Session) -> None:
        pass

    lint = nox.env("lint", venv_backend="none")

    @lint.task
    def run(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[],
        envdir=".nox",
        noxfile=str(tmp_path / "noxfile.py"),
        sessions=["lint:run"],
        extra_pythons=["3.13"],
        force_pythons=["3.13"],
        pythons=(),
        keywords=(),
        tags=None,
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    result = nox.tasks.filter_manifest(manifest, config)
    assert result is manifest

    # Selecting the located env itself does error, cleanly.
    manifest = Manifest(nox.registry.get_registry(), config)
    manifest.filter_by_name(["dev"])
    with pytest.raises(ValueError, match="placeholder"):
        manifest.check_location_collisions()


def test_inexact_env_recreated_on_change(tmp_path: Path) -> None:
    make_provision_env(tmp_path, dependencies=["requests", "six"])
    execute_provision(tmp_path, reused=False)

    nox.registry.reset()
    env2 = make_provision_env(tmp_path, dependencies=["requests"])
    config = nox._options.options.namespace(
        posargs=[],
        envdir=str(tmp_path / ".nox"),
        noxfile=str(tmp_path / "noxfile.py"),
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    fake_venv = mock.MagicMock()
    fake_venv.env = {}
    fake_venv._reused = True
    fake_venv.venv_backend = "uv"
    with mock.patch(
        "nox.sessions.get_virtualenv", return_value=fake_venv
    ) as get_virtualenv:
        for session in manifest:
            assert session.execute()
    # Stale + additive sync: the venv is recreated, not synced in place.
    assert get_virtualenv.call_count == 2
    assert get_virtualenv.call_args.kwargs["reuse_existing"] is False
    assert env2.sync_calls == 1


class ExactTrackingEnvironment(TrackingEnvironment):
    sync_is_exact = True


def test_exact_env_synced_in_place_on_change(tmp_path: Path) -> None:
    env = ExactTrackingEnvironment("dev", dependencies=["requests", "six"])

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    (tmp_path / ".nox" / "dev").mkdir(parents=True, exist_ok=True)
    execute_provision(tmp_path, reused=False)

    nox.registry.reset()
    env2 = ExactTrackingEnvironment("dev", dependencies=["requests"])

    @env2.task
    def sync2(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[],
        envdir=str(tmp_path / ".nox"),
        noxfile=str(tmp_path / "noxfile.py"),
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    fake_venv = mock.MagicMock()
    fake_venv.env = {}
    fake_venv._reused = True
    fake_venv.venv_backend = "uv"
    with mock.patch(
        "nox.sessions.get_virtualenv", return_value=fake_venv
    ) as get_virtualenv:
        for session in manifest:
            assert session.execute()
    assert get_virtualenv.call_count == 1
    assert env2.sync_calls == 1


def test_backend_none_with_dependencies_clean_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    env = nox.env("dev", venv_backend="none", dependencies=["six"])

    @env.task
    def sync(session: nox.Session) -> None:
        pass

    config = nox._options.options.namespace(
        posargs=[],
        envdir=str(tmp_path / ".nox"),
        noxfile=str(tmp_path / "noxfile.py"),
    )
    manifest = Manifest(nox.registry.get_registry(), config)
    result = manifest["dev:sync"].execute()
    assert not result
    assert any(
        "does not have a virtualenv" in record.message for record in caplog.records
    )
