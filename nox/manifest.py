# Copyright 2017 Alethea Katherine Flowers
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

__lazy_modules__ = {
    "ast",
    "itertools",
    "nox._resolver",
    "nox.logger",
    "nox.registry",
    "nox.sessions",
    "operator",
}

import ast
import functools
import itertools
import operator
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from nox._decorators import Call, Func
from nox._resolver import CycleError, lazy_stable_topo_sort
from nox.logger import logger
from nox.registry import RegistryData
from nox.sessions import Session, SessionRunner

if TYPE_CHECKING:
    import argparse
    from collections.abc import Iterable, Iterator, Sequence

    from nox._typing import Python
    from nox.environments import Environment

__all__ = ["WARN_PYTHONS_IGNORED", "Manifest", "keyword_match"]


def __dir__() -> list[str]:
    return __all__


WARN_PYTHONS_IGNORED = "python_ignored"


def _unique_list(*args: str) -> list[str]:
    """Return a list without duplicates, while preserving order."""
    return list(dict.fromkeys(args))


class Manifest:
    """Session manifest.

    The session manifest provides the source of truth for the sequence of
    sessions that should be run by Nox.

    It is possible for this to be mutated during execution. This allows for
    useful use cases, such as for one session to "notify" another or
    "chain" to another.

    Args:
        session_functions (Mapping[str, function]): The registry of discovered
            session functions.
        global_config (.nox.main.GlobalConfig): The global configuration.
        module_docstring (Optional[str]): The user noxfile.py docstring.
            Defaults to `None`.
    """

    def __init__(
        self,
        session_functions: Mapping[str, Func] | RegistryData,
        global_config: argparse.Namespace,
        module_docstring: str | None = None,
    ) -> None:
        self._all_sessions: list[SessionRunner] = []
        self._queue: list[SessionRunner] = []
        self._consumed: list[SessionRunner] = []
        self._config: argparse.Namespace = global_config
        self.module_docstring: str | None = module_docstring
        self._aliases: dict[str, tuple[str, ...]] = {}
        self._extra_requirements_cache: dict[str, list[str]] | None = None

        # Create the sessions based on the provided session functions.
        if isinstance(session_functions, RegistryData):
            self._aliases = dict(session_functions.aliases)
            for env_name, env in session_functions.envs.items():
                tasks = session_functions.tasks.get(env_name, {})
                if env._session_compat:
                    # Classic sessions keep the historical expansion (and
                    # per-session environment directories) exactly.
                    for session in self.make_session(env_name, tasks[env_name]):
                        self.add_session(session)
                else:
                    for session in self._make_env_sessions(env, tasks):
                        self.add_session(session)
            self._warn_shadowing_aliases()
        else:
            for name, func in session_functions.items():
                for session in self.make_session(name, func):
                    self.add_session(session)

    def check_location_collisions(self) -> None:
        """Error if two selected environment instances share one location.

        Checked over the selected sessions (not all sessions), so an
        unselected environment cannot break an unrelated invocation — e.g.
        --force-python temporarily multiplying a located environment.
        """
        locations: dict[str, str] = {}
        location_bases: dict[str, str | None] = {}
        seen_runners: set[int] = set()
        for session in self._queue:
            env_runner = session.env_runner
            environment = env_runner.environment
            if (
                environment is None
                or environment.location is None
                or id(env_runner) in seen_runners
            ):
                continue
            seen_runners.add(id(env_runner))
            resolved = os.path.normpath(env_runner.envdir)
            other = locations.setdefault(resolved, env_runner.friendly_name)
            other_base = location_bases.setdefault(resolved, session.env_base_name)
            if other == env_runner.friendly_name:
                continue
            if other_base == session.env_base_name:
                msg = (
                    f"Multiple instances of environment "
                    f"{session.env_base_name!r} resolve to the location "
                    f"{resolved!r}; add a {{name}} or {{python}} placeholder "
                    "to its location."
                )
            else:
                msg = (
                    f"Environments {other!r} and {env_runner.friendly_name!r} "
                    f"both resolve to the location {resolved!r}."
                )
            raise ValueError(msg)

    def __contains__(self, needle: str | SessionRunner) -> bool:
        return (
            needle in self._queue
            or needle in self._consumed
            or any(
                session.name == needle or needle in session.signatures
                for session in itertools.chain(self._queue, self._consumed)
            )
        )

    def __iter__(self) -> Manifest:
        return self

    def __getitem__(self, key: str) -> SessionRunner:
        for session in itertools.chain(self._queue, self._consumed):
            if session.name == key or key in session.signatures:
                return session
        raise KeyError(key)

    def __next__(self) -> SessionRunner:
        """Return the next item in the queue.

        Raises:
            StopIteration: If the queue has been entirely consumed.
        """
        if not self._queue:
            raise StopIteration
        session = self._queue.pop(0)
        self._consumed.append(session)
        return session

    def __len__(self) -> int:
        return len(self._queue) + len(self._consumed)

    def list_all_sessions(self) -> Iterator[tuple[SessionRunner, bool]]:
        """Yields all sessions and whether or not they're selected."""
        for session in self._all_sessions:
            yield session, session in self._queue

    @property
    def all_sessions_by_signature(self) -> dict[str, SessionRunner]:
        return {
            signature: session
            for session in self._all_sessions
            for signature in session.signatures
        }

    @property
    def parametrized_sessions_by_name(self) -> dict[str, list[SessionRunner]]:
        """Returns a mapping from names to all sessions that are parameterizations of
        the ``@session`` with each name.

        The sessions in each returned list will occur in the same order as they occur in
        ``self._all_sessions``.
        """
        parametrized_sessions = filter(operator.attrgetter("multi"), self._all_sessions)
        key = operator.attrgetter("name")
        # Note that ``sorted`` uses a stable sorting algorithm.
        return {
            name: list(sessions_parametrizing_name)
            for name, sessions_parametrizing_name in itertools.groupby(
                sorted(parametrized_sessions, key=key), key
            )
        }

    def add_session(self, session: SessionRunner) -> None:
        """Add the given session to the manifest.

        Args:
            session (~nox.sessions.Session): A session object, such as
                one returned from ``make_session``.
        """
        if session not in self._all_sessions:
            self._all_sessions.append(session)
            self._extra_requirements_cache = None
        if session not in self._queue:
            self._queue.append(session)

    def filter_by_name(self, specified_sessions: Iterable[str]) -> None:
        """Filter sessions in the queue based on the user-specified names.

        A specified name may be a session/task identifier (``env:task`` or a
        classic session name), an alias, an environment name (which selects
        the environment's default tasks), or a bare task name if that task
        name only exists in one environment.

        Args:
            specified_sessions (Sequence[str]): A list of specified
                session names.

        Raises:
            KeyError: If any explicitly listed sessions are not found.
            ValueError: If a bare task name is ambiguous across environments.
        """
        expanded = self._expand_aliases(specified_sessions)

        kinds = {name: self._id_kind(name) for name in dict.fromkeys(expanded)}

        # Filter the sessions remaining in the queue based on
        # whether they are individually specified.
        self._queue = [
            session
            for session_name in expanded
            for session in self._queue
            if _matches_kind(session_name, kinds[session_name], session)
        ]

        # If a session was requested and was not found, complain loudly.
        missing_sessions = [name for name, kind in kinds.items() if kind is None]
        if missing_sessions:
            msg = f"Sessions not found: {', '.join(missing_sessions)}"
            raise KeyError(msg)

    def _id_kind(self, name: str) -> str | None:
        """Classify a user-specified identifier.

        Returns ``"exact"`` (session name/signature), ``"env"`` (environment
        selector), ``"task"`` (unambiguous bare task name), or ``None`` if
        nothing matches. Earlier kinds take precedence.

        Raises:
            ValueError: If ``name`` is an ambiguous bare task name.
        """
        if any(
            _normalized_session_match(name, session) for session in self._all_sessions
        ):
            return "exact"
        env_matches = [
            session
            for session in self._all_sessions
            if session.task_name is not None
            and name in {session.env_base_name, session.env_instance_name}
        ]
        if env_matches:
            if not any(session.func.default for session in env_matches):
                msg = (
                    f"Environment {name!r} has no default tasks; use "
                    f"'{name}:<task>' to select a task."
                )
                raise ValueError(msg)
            return "env"
        task_envs = {
            session.env_base_name
            for session in self._all_sessions
            if session.task_name == name
        }
        if len(task_envs) > 1:
            candidates = ", ".join(sorted(f"{env}:{name}" for env in task_envs if env))
            msg = f"Task {name!r} is ambiguous: {candidates}. Use 'environment:task'."
            raise ValueError(msg)
        if task_envs:
            return "task"
        return None

    def filter_by_default(self) -> None:
        """Filter sessions in the queue based on the default flag."""

        self._queue = [x for x in self._queue if x.func.default]

    def filter_by_python_interpreter(self, specified_pythons: Sequence[str]) -> None:
        """Filter sessions in the queue based on the user-specified
        python interpreter versions.

        Args:
            specified_pythons (Sequence[str]): A list of specified
                python interpreter versions.
        """
        self._queue = [x for x in self._queue if x.func.python in specified_pythons]

    def filter_by_keywords(self, keywords: str) -> None:
        """Filter sessions using pytest-like keyword expressions.

        Args:
            keywords (str): A Python expression of keywords which
                session names are checked against.
        """
        self._queue = [
            x
            for x in self._queue
            if keyword_match(
                keywords,
                [
                    *x.signatures,
                    *x.tags,
                    x.name,
                    *filter(None, (x.task_name, x.env_base_name, x.env_instance_name)),
                ],
            )
        ]

    def filter_by_tags(self, tags: Iterable[str]) -> None:
        """Filter sessions by their tags.

        Args:
            tags (list[str]): A list of tags which session names
                are checked against.
        """
        self._queue = [x for x in self._queue if set(x.tags).intersection(tags)]

    def add_dependencies(self) -> None:
        """Add direct and recursive dependencies to the queue.

        Raises:
            KeyError: If any depended-on sessions are not found.
            ~nox._resolver.CycleError: If a dependency cycle is encountered.
        """
        sessions_by_id = self.all_sessions_by_signature

        # For each session that was parametrized from a list of Pythons, create a fake
        # parent session that depends on it.
        parent_sessions: set[SessionRunner] = set()
        for (
            parent_name,
            parametrized_sessions,
        ) in self.parametrized_sessions_by_name.items():
            parent_func = _null_session_func.copy()
            parent_func.requires = [
                session.signatures[0] for session in parametrized_sessions
            ]
            parent_session = SessionRunner(
                parent_name, [], parent_func, self._config, self, multi=False
            )
            parent_sessions.add(parent_session)
            sessions_by_id[parent_name] = parent_session

        # Aliases, environment selectors, and unambiguous bare task names are
        # also allowed in ``requires``; represent each as a fake parent that
        # depends on its expansion.
        for extra_name, targets in self._extra_requirements().items():
            if extra_name in sessions_by_id:
                continue
            parent_func = _null_session_func.copy()
            parent_func.requires = targets
            parent_session = SessionRunner(
                extra_name, [], parent_func, self._config, self, multi=False
            )
            parent_sessions.add(parent_session)
            sessions_by_id[extra_name] = parent_session

        # Construct the dependency graph. Note that this is done lazily with iterators
        # so that we won't raise if a session that doesn't actually need to run declares
        # missing/improper dependencies.
        dependency_graph = {
            session: session.get_direct_dependencies(sessions_by_id)
            for session in sessions_by_id.values()
        }

        # Sessions without any signatures (e.g. the placeholder session created
        # when a parametrized session has an empty list of parameters) are not
        # in ``sessions_by_id``, so add any missing queued sessions to the graph.
        for session in self._queue:
            dependency_graph.setdefault(
                session, session.get_direct_dependencies(sessions_by_id)
            )

        # Resolve the dependency graph.
        root = cast("SessionRunner", object())  # sentinel
        try:
            resolved_graph = list(
                lazy_stable_topo_sort({**dependency_graph, root: self._queue}, root)
            )
        except CycleError as exc:
            raise CycleError(
                "Sessions are in a dependency cycle: "
                + " -> ".join(session.name for session in exc.args[1])
            ) from exc

        # Remove fake parent sessions from the resolved graph.
        self._queue = [
            session for session in resolved_graph if session not in parent_sessions
        ]

    def _expand_aliases(self, names: Iterable[str]) -> list[str]:
        """Recursively expand aliases; a cycle leaves the name unresolved."""
        expanded: list[str] = []

        def expand(name: str, seen: frozenset[str]) -> None:
            if name in self._aliases and name not in seen:
                for target in self._aliases[name]:
                    expand(target, seen | {name})
            else:
                expanded.append(name)

        for name in names:
            expand(name, frozenset())
        return expanded

    def _warn_shadowing_aliases(self) -> None:
        for alias_name in self._aliases:
            shadowed = sorted(
                {
                    f"{session.env_base_name}:{session.task_name}"
                    for session in self._all_sessions
                    if session.task_name == alias_name
                }
            )
            if shadowed:
                logger.warning(
                    f"Alias {alias_name!r} shadows the task(s) "
                    f"{', '.join(shadowed)}; the alias takes precedence."
                )

    def _extra_requirements(self) -> dict[str, list[str]]:
        """Identifiers usable in ``requires`` beyond signatures and names.

        Maps aliases, environment selectors (which expand to the environment
        or instance's default tasks), and unambiguous bare task names to the
        identifiers they expand to.
        """
        if self._extra_requirements_cache is not None:
            return self._extra_requirements_cache
        extra: dict[str, list[str]] = {
            name: list(targets) for name, targets in self._aliases.items()
        }

        env_tasks: dict[str, dict[str, bool]] = {}
        instance_tasks: dict[str, dict[str, bool]] = {}
        task_envs: dict[str, dict[str, None]] = {}
        for session in self._all_sessions:
            if session.task_name is None:
                continue
            assert session.env_base_name is not None
            env_defaults = env_tasks.setdefault(session.env_base_name, {})
            env_defaults[session.name] = (
                env_defaults.get(session.name, False) or session.func.default
            )
            if session.env_instance_name != session.env_base_name:
                assert session.env_instance_name is not None
                instance_tasks.setdefault(session.env_instance_name, {})[
                    f"{session.env_instance_name}:{session.task_name}"
                ] = session.func.default
            task_envs.setdefault(session.task_name, {})[session.env_base_name] = None

        for env_name, canonical_names in env_tasks.items():
            defaults = [name for name, default in canonical_names.items() if default]
            if defaults:
                extra.setdefault(env_name, defaults)
        for instance_name, signature_names in instance_tasks.items():
            defaults = [name for name, default in signature_names.items() if default]
            if defaults:
                extra.setdefault(instance_name, defaults)
        for task_name, envs in task_envs.items():
            if len(envs) == 1:
                (env_name,) = envs
                extra.setdefault(task_name, [f"{env_name}:{task_name}"])

        self._extra_requirements_cache = extra
        return extra

    def resolve_requirement(
        self, requirement: str, _seen: frozenset[str] = frozenset()
    ) -> list[SessionRunner]:
        """Resolve a ``requires`` entry to the sessions it refers to.

        Raises:
            KeyError: If the requirement cannot be resolved.
        """
        by_signature = self.all_sessions_by_signature
        if requirement in by_signature:
            return [by_signature[requirement]]
        by_name = self.parametrized_sessions_by_name
        if requirement in by_name:
            return list(by_name[requirement])
        extra = self._extra_requirements()
        if requirement in extra and requirement not in _seen:
            seen = _seen | {requirement}
            return [
                session
                for target in extra[requirement]
                for session in self.resolve_requirement(target, seen)
            ]
        raise KeyError(requirement)

    def _make_env_sessions(
        self, env: Environment, tasks: Mapping[str, Func]
    ) -> list[SessionRunner]:
        """Create task runners for an explicit environment.

        All tasks of one concrete environment instance (i.e. per interpreter,
        after expanding a python list) share a single :class:`EnvRunner`.
        """
        runners: list[SessionRunner] = []

        backend = (
            self._config.force_venv_backend
            or env.venv_backend
            or self._config.default_venv_backend
        )
        python: Python = env.python
        env_should_warn: dict[str, Any] = {}
        if backend == "none" and isinstance(python, (list, tuple, set)):
            env_should_warn[WARN_PYTHONS_IGNORED] = python
            python = False

        if self._config.extra_pythons:
            extra_pythons: list[str] = self._config.extra_pythons
            if isinstance(python, (list, tuple, set)):
                python = _unique_list(*python, *extra_pythons)
            elif python:
                assert isinstance(python, str)
                python = _unique_list(python, *extra_pythons)
            elif not python and self._config.force_pythons:
                python = _unique_list(*extra_pythons)

        multi = isinstance(python, (list, tuple, set))
        pythons = list(python) if isinstance(python, (list, tuple, set)) else [python]

        for py in pythons:
            # The on-disk name only gets a python suffix for a python list
            # (matching classic sessions), but the selector always does, so
            # `-s tooling-3.12` works for pinned environments too.
            dir_name = f"{env.name}-{py}" if multi and py else env.name
            selector_name = f"{env.name}-{py}" if py else env.name
            env_runner = None
            for task_name, task_func in tasks.items():
                func = self._bind_task_func(task_func, env, py, env_should_warn)
                for runner in self._make_task_runners(
                    env.name, task_name, func, multi=multi
                ):
                    runner.task_name = task_name
                    runner.env_base_name = env.name
                    runner.env_instance_name = selector_name
                    if env_runner is None:
                        env_runner = runner.env_runner
                        env_runner._name = dir_name
                        env_runner._func = func
                        env_runner.environment = env
                        env_runner.shared = len(tasks) > 1
                    else:
                        runner.env_runner = env_runner
                    runners.append(runner)

        return runners

    def _bind_task_func(
        self,
        task_func: Func,
        env: Environment,
        python: Python,
        env_should_warn: Mapping[str, Any],
    ) -> Func:
        """Copy a task function and fill in the environment-level settings."""
        func = task_func.copy(task_func.name)
        func.python = python
        # Declarative environments are reused (and re-synced when their
        # inputs change) by default; --reuse-venv=never still recreates.
        func.reuse_venv = True if env.reuse_venv is None else env.reuse_venv
        func.venv_backend = env.venv_backend
        func.venv_params = env.venv_params
        func.download_python = env.download_python
        func.tags = _unique_list(*env.tags, *task_func.tags)
        func.should_warn.update(env_should_warn)
        return func

    def _make_task_runners(
        self, env_name: str, task_name: str, func: Func, *, multi: bool
    ) -> list[SessionRunner]:
        """Create the runner(s) for one task in one concrete environment.

        Mirrors the signature scheme of :meth:`make_session`, with the python
        suffix attached to the environment part of the ``env:task`` id.
        """
        canonical = f"{env_name}:{task_name}"
        instance_id = f"{env_name}-{func.python}:{task_name}" if func.python else None

        if not hasattr(func, "parametrize"):
            long_names = []
            if not multi:
                long_names.append(canonical)
            if instance_id:
                long_names.append(instance_id)
            return [
                SessionRunner(
                    canonical, long_names, func, self._config, self, multi=multi
                )
            ]

        sessions = []
        calls = Call.generate_calls(func, func.parametrize)
        for call in calls:
            if call.python != func.python:
                msg = (
                    f"Task {canonical!r} cannot parametrize 'python'; "
                    "set python on the environment instead."
                )
                raise ValueError(msg)
            long_names = []
            if not multi or (
                self._config.force_pythons and call.python in self._config.extra_pythons
            ):
                long_names.append(f"{canonical}{call.session_signature}")
            if instance_id:
                long_names.append(f"{instance_id}{call.session_signature}")
                # Ensure that specifying environment-python will run all
                # parameterizations.
                long_names.append(instance_id)
            sessions.append(
                SessionRunner(
                    canonical, long_names, call, self._config, self, multi=multi
                )
            )

        # Edge case: If the parameters made it such that there were no valid
        # calls, add an empty, do-nothing session.
        if not calls:
            sessions.append(
                SessionRunner(
                    canonical, [], _null_session_func, self._config, self, multi=multi
                )
            )

        return sessions

    def make_session(
        self, name: str, func: Func, *, multi: bool = False
    ) -> list[SessionRunner]:
        """Create a session object from the session function.

        Args:
            name (str): The name of the session.
            func (function): The session function.
            multi (bool): Whether the function is a member of a set of sessions
                with different interpreters.

        Returns:
            Sequence[~nox.session.Session]: A sequence of Session objects
                bound to this manifest and configuration.
        """
        sessions = []

        # If the backend is "none", we won't parametrize `python`.
        backend = (
            self._config.force_venv_backend
            or func.venv_backend
            or self._config.default_venv_backend
        )
        if backend == "none" and isinstance(func.python, (list, tuple, set)):
            # we can not log a warning here since the session is maybe deselected.
            # instead let's set a flag, to warn later when session is actually run.
            func.should_warn[WARN_PYTHONS_IGNORED] = func.python
            func.python = False

        if self._config.extra_pythons:
            # If extra python is provided, expand the func.python list to
            # include additional python interpreters
            extra_pythons: list[str] = self._config.extra_pythons
            if isinstance(func.python, (list, tuple, set)):
                func.python = _unique_list(*func.python, *extra_pythons)
            elif not multi and func.python:
                # If this is multi, but there is only a single interpreter, it
                # is the reentrant case. The extra_python interpreter shouldn't
                # be added in that case. If func.python is False, the session
                # has no backend; if None, it uses the same interpreter as Nox.
                # Otherwise, add the extra specified python.
                assert isinstance(func.python, str)
                func.python = _unique_list(func.python, *extra_pythons)
            elif not func.python and self._config.force_pythons:
                # If a python is forced by the user, but the underlying function
                # has no version parametrised, add it as sole occupant to func.python
                func.python = _unique_list(*extra_pythons)

        # If the func has the python attribute set to a list, we'll need
        # to expand them.
        if isinstance(func.python, (list, tuple, set)):
            for python in func.python:
                single_func = func.copy()
                single_func.python = python
                sessions.extend(self.make_session(name, single_func, multi=True))

            return sessions

        # Simple case: If this function is not parametrized, then make
        # a simple session.
        if not hasattr(func, "parametrize"):
            long_names = []
            if not multi:
                long_names.append(name)
            if func.python:
                long_names.append(f"{name}-{func.python}")

            return [
                SessionRunner(name, long_names, func, self._config, self, multi=multi)
            ]

        # Since this function is parametrized, we need to add a distinct
        # session for each permutation.
        parametrize = func.parametrize
        calls = Call.generate_calls(func, parametrize)
        for call in calls:
            long_names = []
            if not multi or (
                self._config.force_pythons and call.python in self._config.extra_pythons
            ):
                long_names.append(f"{name}{call.session_signature}")

            if func.python:
                long_names.append(f"{name}-{func.python}{call.session_signature}")
                # Ensure that specifying session-python will run all parameterizations.
                long_names.append(f"{name}-{func.python}")

            sessions.append(
                SessionRunner(name, long_names, call, self._config, self, multi=multi)
            )

        # Edge case: If the parameters made it such that there were no valid
        # calls, add an empty, do-nothing session.
        if not calls:
            sessions.append(
                SessionRunner(
                    name, [], _null_session_func, self._config, self, multi=multi
                )
            )

        # Return the list of sessions.
        return sessions

    def notify(
        self, session: str | SessionRunner, posargs: Iterable[str] | None = None
    ) -> bool:
        """Enqueue the specified session in the queue.

        If the session is already in the queue, or has been run already,
        then this is a no-op.

        Args:
            session (Union[str, ~nox.session.Session]): The session to be
                enqueued.
            posargs (Optional[List[str]]): If given, sets the positional
                arguments *only* for the queued session. Otherwise, the
                standard globally available positional arguments will be
                used instead.

        Returns:
            bool: Whether the session was added to the queue.

        Raises:
            ValueError: If the session was not found.
        """
        # Sanity check: If this session is already in the queue, this is
        # a no-op.
        if session in self:
            return False

        # Locate the session in the list of all sessions, and place it at
        # the end of the queue.
        for s in self._all_sessions:
            if s == session or s.name == session or session in s.signatures:  # noqa: PLR1714
                if posargs is not None:
                    s.posargs = list(posargs)
                self._queue.append(s)
                return True

        # Fall back to the shared identifier grammar (aliases, environment
        # selectors, bare task names).
        if isinstance(session, str):
            try:
                resolved = self.resolve_requirement(session)
            except KeyError:
                pass
            else:
                added = False
                for runner in resolved:
                    if runner in self._queue or runner in self._consumed:
                        continue
                    if posargs is not None:
                        runner.posargs = list(posargs)
                    self._queue.append(runner)
                    added = True
                return added

        # The session was not found in the list of sessions.
        msg = f"Session {session} not found."
        raise ValueError(msg)


class KeywordLocals(Mapping[str, bool]):
    """Eval locals using keywords.

    When looking up a local variable the variable name is compared against
    the set of keywords. If the local variable name matches any *substring* of
    any keyword, then the name lookup returns True. Otherwise, the name lookup
    returns False.
    """

    def __init__(self, keywords: Iterable[str]) -> None:
        self._keywords = frozenset(keywords)

    def __getitem__(self, variable_name: str) -> bool:
        return any(variable_name in keyword for keyword in self._keywords)

    def __iter__(self) -> Iterator[str]:
        return iter(self._keywords)

    def __len__(self) -> int:
        return len(self._keywords)


def keyword_match(expression: str, keywords: Iterable[str]) -> Any:
    """See if an expression matches the given set of keywords."""
    # TODO: see if we can use ast.literal_eval here.
    my_locals = KeywordLocals(set(keywords))
    return eval(expression, {}, my_locals)  # noqa: S307


def _null_session_func_(session: Session) -> None:
    """A no-op session for parametrized sessions with no available params."""
    session.skip("This session had no parameters available.")


def _normalized_session_match(session_name: str, session: SessionRunner) -> bool:
    """Checks if session_name matches session."""
    if session_name == session.name or session_name in session.signatures:
        return True
    normalized_name = _normalize_arg(session_name)
    for name in (session.name, *session.signatures):
        equal_rep = normalized_name == _normalize_arg(name)
        if equal_rep:
            return True
    # Exhausted
    return False


def _matches_kind(session_name: str, kind: str | None, session: SessionRunner) -> bool:
    """Checks if session_name, classified by Manifest._id_kind, matches session."""
    if kind == "exact":
        return _normalized_session_match(session_name, session)
    if kind == "env":
        # Selecting an environment runs its default tasks.
        return (
            session.task_name is not None
            and session_name in {session.env_base_name, session.env_instance_name}
            and session.func.default
        )
    if kind == "task":
        return session.task_name == session_name
    return False


@functools.cache
def _normalize_arg(arg: str) -> str:
    """Normalize arg for comparison."""
    # For env:task ids only the task part is Python-like; normalize it alone.
    # A colon after "(" is parametrize-argument content, not a separator.
    head, sep, tail = arg.partition(":")
    if sep and "(" not in head:
        return f"{head}:{_normalize_call(tail)}"
    return _normalize_call(arg)


def _normalize_call(arg: str) -> str:
    try:
        return str(ast.dump(ast.parse(arg)))
    except (TypeError, SyntaxError):
        return arg


_null_session_func = Func(_null_session_func_, python=False)
