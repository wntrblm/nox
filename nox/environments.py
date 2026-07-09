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

__lazy_modules__ = {
    f"{__spec__.parent}._decorators",
    "functools",
    "hashlib",
    "nox.virtualenv",
}

import functools
import hashlib
import os
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, overload

import nox.virtualenv

from ._decorators import Func

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ._typing import Python
    from .sessions import Session

    RawFunc = Callable[..., Any]

__all__ = [
    "Environment",
    "PylockEnvironment",
    "RegistryData",
    "UvProjectEnvironment",
    "alias",
    "env",
    "get_registry_data",
    "register_env",
    "register_session_pair",
    "register_task",
    "reset_registry",
    "validate_name",
]


def __dir__() -> list[str]:
    return __all__


def validate_name(name: str, kind: str = "An environment") -> None:
    """Reject names that would break ``env:task`` identifiers."""
    if not name:
        msg = f"{kind} name cannot be empty."
        raise ValueError(msg)
    for char in ":()":
        if char in name:
            msg = f"{kind} name cannot contain {char!r}: {name!r}"
            raise ValueError(msg)


def _file_hash(path: str, *, kind: str) -> str:
    """Hash a provisioning input file for the environment stamp."""
    try:
        with open(path, "rb") as file:
            return hashlib.sha256(file.read()).hexdigest()
    except FileNotFoundError:
        msg = f"The {kind} {path!r} does not exist."
        raise FileNotFoundError(msg) from None


class Environment:
    """A declarative environment (virtualenv + how to provision it).

    Tasks are attached with the :meth:`task` decorator and run inside this
    environment, sharing a single virtualenv. Instantiating an ``Environment``
    registers it globally; subclasses can customize provisioning.
    """

    def __init__(
        self,
        name: str,
        *,
        python: Python = None,
        venv_backend: str | None = None,
        venv_params: Sequence[str] = (),
        reuse_venv: bool | None = None,
        download_python: Literal["auto", "never", "always"] | None = None,
        tags: Sequence[str] | None = None,
        dependencies: Sequence[str] = (),
        location: str | os.PathLike[str] | None = None,
        setup_stamp: str | None = None,
        register: bool = True,
    ) -> None:
        self.name = name
        self.python = python
        self.venv_backend = venv_backend
        self.venv_params = venv_params
        self.reuse_venv = reuse_venv
        self.download_python = download_python
        self.tags = list(tags or [])
        self.dependencies = list(dependencies)
        self.location = os.fspath(location) if location is not None else None
        self.setup_func: Callable[[Session], None] | None = None
        self.setup_stamp = setup_stamp
        # True for environments implicitly created by @nox.session; drives
        # the legacy naming/envdir behavior.
        self._session_compat = False

        if register:
            register_env(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

    def setup(self, func: Callable[[Session], None]) -> Callable[[Session], None]:
        """Designate the decorated function as this environment's setup hook.

        The hook runs after the declarative dependencies are synced, and only
        when the environment is created or out of date. Since nox cannot know
        when the hook's *effect* changes, an environment with a setup hook is
        re-synced on every run unless ``setup_stamp`` is set; bump that value
        whenever the hook's behavior changes.
        """
        if self.setup_func is not None:
            msg = f"The environment {self.name!r} already has a setup function."
            raise ValueError(msg)
        self.setup_func = func
        return func

    def stamp_data(self) -> dict[str, Any] | None:
        """The provisioning inputs, used to decide when to re-sync.

        Returning ``None`` marks the environment as unstampable: it is synced
        on every run. Subclasses should extend the returned dict with the
        content hashes of their inputs (e.g. a lock file).
        """
        if self.setup_func is not None and self.setup_stamp is None:
            return None
        data: dict[str, Any] = {
            "kind": "dependencies",
            "dependencies": list(self.dependencies),
        }
        if self.setup_stamp is not None:
            data["setup_stamp"] = self.setup_stamp
        return data

    @property
    def sync_is_exact(self) -> bool:
        """Whether :meth:`sync` makes the environment exactly match its inputs.

        When False (plain pip installs are additive), a stale environment is
        recreated instead of re-synced in place, so removed dependencies
        actually disappear.
        """
        return False

    def sync(self, session: Session) -> None:
        """Install this environment's declared dependencies.

        Subclasses override this to install from lock files; the base
        implementation installs ``dependencies`` with pip/uv.
        """
        if self.dependencies:
            session.install(*self.dependencies)

    @overload
    def task(self, func: RawFunc | Func, /) -> Func: ...

    @overload
    def task(
        self,
        func: None = ...,
        /,
        *,
        name: str | None = ...,
        tags: Sequence[str] | None = ...,
        default: bool = ...,
        requires: Sequence[str] | None = ...,
    ) -> Callable[[RawFunc | Func], Func]: ...

    def task(
        self,
        func: RawFunc | Func | None = None,
        /,
        *,
        name: str | None = None,
        tags: Sequence[str] | None = None,
        default: bool = True,
        requires: Sequence[str] | None = None,
    ) -> Func | Callable[[RawFunc | Func], Func]:
        """Designate the decorated function as a task in this environment.

        Works with and without parentheses, like ``@nox.session``.
        """
        if func is None:
            return functools.partial(
                self.task, name=name, tags=tags, default=default, requires=requires
            )

        if isinstance(func, Func):
            func = func.func

        task_name = name or func.__name__
        validate_name(task_name, "A task")

        fn = Func(
            func,
            # Interpreter/venv settings are environment-level; they are filled
            # in from the (expanded) environment when the manifest is built.
            name=f"{self.name}:{task_name}",
            tags=tags,
            default=default,
            requires=requires,
        )
        fn.task_name = task_name
        fn.env = self

        register_task(self, task_name, fn)
        return fn


class PylockEnvironment(Environment):
    """An environment installed from a PEP 751 ``pylock.toml`` file.

    The lock file is installed with ``uv pip sync``, so the environment
    exactly matches the lock; extra ``dependencies`` are installed after.
    Available as ``nox.env.pylock``.
    """

    def __init__(
        self,
        name: str,
        *,
        lockfile: str | os.PathLike[str] = "pylock.toml",
        **kwargs: Any,
    ) -> None:
        super().__init__(name, **kwargs)
        self.lockfile = os.fspath(lockfile)

    def stamp_data(self) -> dict[str, Any] | None:
        data = super().stamp_data()
        if data is None:
            return None
        data["kind"] = "pylock"
        data["lockfile"] = self.lockfile
        data["lockfile_hash"] = _file_hash(self.lockfile, kind="lock file")
        return data

    @property
    def sync_is_exact(self) -> bool:
        # `uv pip sync` is exact; extra dependencies are installed after it,
        # additively.
        return not self.dependencies

    def sync(self, session: Session) -> None:
        if not nox.virtualenv.HAS_UV:
            msg = (
                f"Environment {self.name!r} installs from a pylock file, "
                "which requires uv to be available."
            )
            raise RuntimeError(msg)
        if not session.virtualenv.is_sandboxed or session.venv_backend not in {
            "uv",
            "virtualenv",
            "venv",
        }:
            msg = (
                f"Environment {self.name!r} installs from a pylock file, which "
                f"requires a virtualenv-style backend, not {session.venv_backend!r}."
            )
            raise RuntimeError(msg)
        # uv targets the session's venv through the VIRTUAL_ENV variable.
        session.run_install(
            nox.virtualenv.UV, "pip", "sync", self.lockfile, external=True, silent=True
        )
        super().sync(session)


class UvProjectEnvironment(Environment):
    """An environment synced from a uv project's ``uv.lock``.

    Runs ``uv sync --locked`` against the project owning the lock file,
    targeting this environment. Available as ``nox.env.uv``.
    """

    def __init__(
        self,
        name: str,
        *,
        lockfile: str | os.PathLike[str] = "uv.lock",
        groups: Sequence[str] = (),
        extras: Sequence[str] = (),
        all_extras: bool = False,
        no_default_groups: bool = False,
        no_install_project: bool = False,
        sync_args: Sequence[str] = (),
        venv_backend: str = "uv",
        **kwargs: Any,
    ) -> None:
        if venv_backend != "uv":
            msg = f"Environment {name!r} syncs a uv project and requires the 'uv' venv backend."
            raise ValueError(msg)
        super().__init__(name, venv_backend="uv", **kwargs)
        self.lockfile = os.fspath(lockfile)
        self.groups = list(groups)
        self.extras = list(extras)
        self.all_extras = all_extras
        self.no_default_groups = no_default_groups
        self.no_install_project = no_install_project
        self.sync_args = list(sync_args)

    def _sync_command(self) -> list[str]:
        project_dir = os.path.dirname(os.path.abspath(self.lockfile))
        command = ["sync", "--locked", f"--project={project_dir}"]
        command.extend(f"--group={group}" for group in self.groups)
        command.extend(f"--extra={extra}" for extra in self.extras)
        if self.all_extras:
            command.append("--all-extras")
        if self.no_default_groups:
            command.append("--no-default-groups")
        if self.no_install_project:
            command.append("--no-install-project")
        command.extend(self.sync_args)
        return command

    def stamp_data(self) -> dict[str, Any] | None:
        data = super().stamp_data()
        if data is None:
            return None
        data["kind"] = "uv"
        data["lockfile"] = self.lockfile
        data["lockfile_hash"] = _file_hash(self.lockfile, kind="lock file")
        data["command"] = self._sync_command()
        return data

    @property
    def sync_is_exact(self) -> bool:
        # `uv sync` is exact; extra dependencies are installed after it,
        # additively.
        return not self.dependencies

    def sync(self, session: Session) -> None:
        # uv targets the session's venv through UV_PROJECT_ENVIRONMENT, which
        # only the uv backend sets; on any other backend `uv sync` would fall
        # back to the *project's* own .venv and clobber it.
        if session.venv_backend != "uv":
            msg = (
                f"Environment {self.name!r} syncs a uv project and must run "
                f"on the 'uv' venv backend, not {session.venv_backend!r} "
                "(is --force-venv-backend or --no-venv overriding it?)."
            )
            raise RuntimeError(msg)
        session.run_install(
            nox.virtualenv.UV, *self._sync_command(), external=True, silent=True
        )
        super().sync(session)


class _EnvAPI:
    """The ``nox.env`` callable namespace.

    Calling it creates a plain declarative :class:`Environment`; specialized
    environment types (lock file support, etc.) hang off it as attributes.
    """

    pylock = PylockEnvironment
    uv = UvProjectEnvironment

    def __call__(self, name: str, /, **kwargs: Any) -> Environment:
        return Environment(name, **kwargs)


env = _EnvAPI()


class RegistryData(NamedTuple):
    """The full contents of the session registry."""

    envs: dict[str, Environment]
    tasks: dict[str, dict[str, Func]]
    aliases: dict[str, tuple[str, ...]]


_ENVS: dict[str, Environment] = {}
_TASKS: dict[str, dict[str, Func]] = {}
_ALIASES: dict[str, tuple[str, ...]] = {}


def reset_registry() -> None:
    _ENVS.clear()
    _TASKS.clear()
    _ALIASES.clear()


def _check_global_name(name: str, kind: str) -> None:
    if name in _ENVS:
        what = "session" if _ENVS[name]._session_compat else "environment"
        msg = f"A {what} named {name!r} is already registered; cannot register {kind} {name!r}."
        raise ValueError(msg)
    if name in _ALIASES:
        msg = f"An alias named {name!r} is already registered; cannot register {kind} {name!r}."
        raise ValueError(msg)


def register_env(environment: Environment) -> None:
    """Register an environment in the global registry."""
    validate_name(environment.name)
    _check_global_name(environment.name, "environment")
    _ENVS[environment.name] = environment
    _TASKS.setdefault(environment.name, {})


def register_task(environment: Environment, task_name: str, fn: Func) -> None:
    """Register a task under its environment."""
    if environment.name not in _ENVS:
        msg = f"The environment {environment.name!r} is not registered."
        raise ValueError(msg)
    tasks = _TASKS[environment.name]
    if task_name in tasks:
        msg = (
            f"The task {task_name!r} is already registered in "
            f"environment {environment.name!r}."
        )
        raise ValueError(msg)
    tasks[task_name] = fn


def register_session_pair(environment: Environment, fn: Func) -> None:
    """Register a classic session: an environment/task pair sharing a name.

    The name is not validated, since classic session names predate the
    ``env:task`` grammar; ``@nox.session`` warns about conflicting names.
    """
    environment._session_compat = True
    _ENVS[environment.name] = environment
    _TASKS[environment.name] = {environment.name: fn}
    fn.task_name = environment.name
    fn.env = environment


def alias(name: str, /, *targets: str) -> None:
    """Register a global alias that expands to one or more sessions.

    Args:
        name: The alias name; shares a namespace with environments.
        targets: One or more session identifiers (e.g. ``"tooling:lint"``).
    """
    validate_name(name, "An alias")
    if not targets:
        msg = f"Alias {name!r} needs at least one target."
        raise ValueError(msg)
    _check_global_name(name, "alias")
    _ALIASES[name] = targets


def get_registry_data() -> RegistryData:
    """Return a shallow copy of the full registry."""
    return RegistryData(
        envs=dict(_ENVS),
        tasks={name: dict(tasks) for name, tasks in _TASKS.items()},
        aliases=dict(_ALIASES),
    )
