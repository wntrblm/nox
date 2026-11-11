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
    "functools",
    "hashlib",
    "nox.registry",
    "nox.virtualenv",
    f"{__spec__.parent}._decorators",
}

import functools
import hashlib
import os
from typing import TYPE_CHECKING, Any, Literal, overload

import nox.registry
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
    "UvProjectEnvironment",
    "env",
]


def __dir__() -> list[str]:
    return __all__


def _file_hash(path: str, *, kind: str) -> str:
    """Hash a provisioning input file for the environment stamp."""
    try:
        with open(path, "rb") as file:
            return hashlib.sha256(file.read()).hexdigest()
    except FileNotFoundError:
        msg = f"The {kind} {path!r} does not exist."
        raise FileNotFoundError(msg) from None


_FILE_OPTIONS = frozenset({"-r", "-c", "--requirement", "--constraint"})
_PROJECT_FILES = ("pyproject.toml", "setup.py", "setup.cfg")


def _implicit_inputs(dependencies: Sequence[str]) -> list[str]:
    """Files whose contents affect installing ``dependencies``.

    Covers ``-r``/``-c`` files and the metadata files of local project
    directories (``.``, ``-e .``). Source changes of an editable install
    are not inputs, and a local project's build backend may read files
    other than these; list them with ``inputs=`` if so.
    """
    files: list[str] = []
    args = iter(dependencies)
    for arg in args:
        if arg in _FILE_OPTIONS:
            files.append(next(args, ""))
            continue
        option, sep, value = arg.partition("=")
        if sep and option in _FILE_OPTIONS:
            files.append(value)
            continue
        if arg in {"-e", "--editable"}:
            requirement = next(args, "")
        elif arg.startswith("--editable="):
            requirement = arg.removeprefix("--editable=")
        elif arg.startswith("-e"):
            requirement = arg[2:]
        elif arg.startswith("-"):
            continue
        else:
            requirement = arg
        # Strip extras: "./pkg[dev]" -> "./pkg".
        path = requirement.partition("[")[0]
        if path and os.path.isdir(path):
            files.extend(
                os.path.join(path, name)
                for name in _PROJECT_FILES
                if os.path.isfile(os.path.join(path, name))
            )
    return [file for file in files if file]


class Environment:
    """A declarative environment (virtualenv + how to provision it).

    Tasks are attached with the :meth:`task` decorator and run inside this
    environment, sharing a single virtualenv. Instantiating an ``Environment``
    registers it globally; subclasses can customize provisioning. Available
    as ``nox.env.standard``.
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
        inputs: Sequence[str | os.PathLike[str]] = (),
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
        self.inputs = [os.fspath(path) for path in inputs]
        self.location = os.fspath(location) if location is not None else None
        self.setup_func: Callable[[Session], None] | None = None
        self.setup_stamp = setup_stamp

        if register:
            nox.registry.register_env(self)

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
            "inputs": self._input_hashes(),
        }
        if self.setup_stamp is not None:
            data["setup_stamp"] = self.setup_stamp
        return data

    def _input_hashes(self, *extra: str) -> dict[str, str]:
        """Content hashes of explicit ``inputs`` plus implicit ones.

        Explicit inputs must exist; implicit ones (``-r`` files, local
        project metadata, ``extra``) are only hashed when present.
        """
        hashes = {path: _file_hash(path, kind="input") for path in self.inputs}
        for path in (*_implicit_inputs(self.dependencies), *extra):
            if path not in hashes and os.path.isfile(path):
                hashes[path] = _file_hash(path, kind="input")
        return hashes

    def needs_venv(self) -> bool:
        """Whether provisioning installs into the environment.

        If True, Nox refuses to provision this environment without a
        virtualenv (``venv_backend="none"``). Subclasses that override
        :meth:`sync` should override this too.
        """
        return bool(self.dependencies) or self.setup_func is not None

    def sync_is_exact(self, session: Session) -> bool:  # noqa: ARG002
        """Whether :meth:`sync` makes the environment exactly match its inputs.

        When False (plain pip installs are additive), a stale environment is
        recreated instead of re-synced in place, so removed dependencies
        actually disappear. Takes the session, since this can depend on the
        venv backend actually in use.
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
        explicit: bool = ...,
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
        explicit: bool = False,
        requires: Sequence[str] | None = None,
    ) -> Func | Callable[[RawFunc | Func], Func]:
        """Designate the decorated function as a task in this environment.

        Works with and without parentheses, like ``@nox.session``.

        ``default=False`` keeps the task out of a bare ``nox`` run.
        ``explicit=True`` keeps it out of environment selectors such as
        ``nox -s env`` or ``requires=["env"]``; it then only runs when named
        as ``env:task`` or through an alias.
        """
        if func is None:
            return functools.partial(
                self.task,
                name=name,
                tags=tags,
                default=default,
                explicit=explicit,
                requires=requires,
            )

        if isinstance(func, Func):
            func = func.func

        task_name = name or func.__name__
        nox.registry.validate_name(task_name, "A task")

        fn = Func(
            func,
            # Interpreter/venv settings are environment-level; they are filled
            # in from the (expanded) environment when the manifest is built.
            name=f"{self.name}:{task_name}",
            tags=tags,
            default=default,
            explicit=explicit,
            requires=requires,
        )
        fn.task_name = task_name
        fn.env = self

        nox.registry.register_task(self, task_name, fn)
        return fn


class PylockEnvironment(Environment):
    """An environment installed from a PEP 751 ``pylock.toml`` file.

    With uv available, the lock file is installed with ``uv pip sync``, so
    the environment exactly matches the lock. Otherwise, or on backends uv
    cannot target (such as conda), it is installed with ``pip install -r``
    (pip 25.1+; 26.3+ for ``groups`` and ``extras``). Extra ``dependencies``
    are installed after. Available as ``nox.env.pylock``.
    """

    _UV_BACKENDS = frozenset({"uv", "virtualenv", "venv"})

    def __init__(
        self,
        name: str,
        *,
        lockfile: str | os.PathLike[str] = "pylock.toml",
        groups: Sequence[str] = (),
        extras: Sequence[str] = (),
        python: Python = None,
        venv_backend: str | None = None,
        venv_params: Sequence[str] = (),
        reuse_venv: bool | None = None,
        download_python: Literal["auto", "never", "always"] | None = None,
        tags: Sequence[str] | None = None,
        dependencies: Sequence[str] = (),
        inputs: Sequence[str | os.PathLike[str]] = (),
        location: str | os.PathLike[str] | None = None,
        setup_stamp: str | None = None,
        register: bool = True,
    ) -> None:
        super().__init__(
            name,
            python=python,
            venv_backend=venv_backend,
            venv_params=venv_params,
            reuse_venv=reuse_venv,
            download_python=download_python,
            tags=tags,
            dependencies=dependencies,
            inputs=inputs,
            location=location,
            setup_stamp=setup_stamp,
            register=register,
        )
        self.lockfile = os.fspath(lockfile)
        self.groups = list(groups)
        self.extras = list(extras)

    def stamp_data(self) -> dict[str, Any] | None:
        data = super().stamp_data()
        if data is None:
            return None
        data["kind"] = "pylock"
        data["lockfile"] = self.lockfile
        data["lockfile_hash"] = _file_hash(self.lockfile, kind="lock file")
        data["groups"] = self.groups
        data["extras"] = self.extras
        return data

    def needs_venv(self) -> bool:
        return True

    def sync_is_exact(self, session: Session) -> bool:
        # `uv pip sync` is exact; pip and extra dependencies are additive.
        return self._uses_uv(session) and not self.dependencies

    def _uses_uv(self, session: Session) -> bool:
        return nox.virtualenv.HAS_UV and session.venv_backend in self._UV_BACKENDS

    def sync(self, session: Session) -> None:
        if not session.virtualenv.is_sandboxed:
            msg = (
                f"Environment {self.name!r} installs from a pylock file and "
                "requires a virtual environment."
            )
            raise RuntimeError(msg)
        if self._uses_uv(session):
            # uv targets the session's venv through the VIRTUAL_ENV variable.
            session.run_install(
                nox.virtualenv.UV,
                "pip",
                "sync",
                self.lockfile,
                *(f"--group={group}" for group in self.groups),
                *(f"--extra={extra}" for extra in self.extras),
                external=True,
                silent=True,
            )
        else:
            requirement = self.lockfile
            if self.extras:
                requirement += f"[{','.join(self.extras)}]"
            session.install(
                "-r",
                requirement,
                *(f"--group={self.lockfile}:{group}" for group in self.groups),
            )
        super().sync(session)


class UvProjectEnvironment(Environment):
    """An environment synced from a uv project's ``uv.lock``.

    Runs ``uv sync --locked`` against the project owning the lock file,
    targeting this environment. With ``frozen=True``, it runs
    ``uv sync --frozen``, which does not check that the lock file is up to
    date. Available as ``nox.env.uv_project``.
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
        frozen: bool = False,
        sync_args: Sequence[str] = (),
        python: Python = None,
        venv_backend: str = "uv",
        venv_params: Sequence[str] = (),
        reuse_venv: bool | None = None,
        download_python: Literal["auto", "never", "always"] | None = None,
        tags: Sequence[str] | None = None,
        dependencies: Sequence[str] = (),
        inputs: Sequence[str | os.PathLike[str]] = (),
        location: str | os.PathLike[str] | None = None,
        setup_stamp: str | None = None,
        register: bool = True,
    ) -> None:
        if venv_backend != "uv":
            msg = f"Environment {name!r} syncs a uv project and requires the 'uv' venv backend."
            raise ValueError(msg)
        super().__init__(
            name,
            python=python,
            venv_backend=venv_backend,
            venv_params=venv_params,
            reuse_venv=reuse_venv,
            download_python=download_python,
            tags=tags,
            dependencies=dependencies,
            inputs=inputs,
            location=location,
            setup_stamp=setup_stamp,
            register=register,
        )
        self.lockfile = os.fspath(lockfile)
        self.groups = list(groups)
        self.extras = list(extras)
        self.all_extras = all_extras
        self.no_default_groups = no_default_groups
        self.no_install_project = no_install_project
        self.frozen = frozen
        self.sync_args = list(sync_args)

    def _sync_command(self) -> list[str]:
        project_dir = os.path.dirname(os.path.abspath(self.lockfile))
        lock_flag = "--frozen" if self.frozen else "--locked"
        command = ["sync", lock_flag, f"--project={project_dir}"]
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
        # `--locked` only validates when the sync actually runs, so the
        # project file (and the project's entry points) must be an input.
        pyproject = os.path.join(os.path.dirname(self.lockfile), "pyproject.toml")
        data["inputs"] = self._input_hashes(pyproject)
        data["command"] = self._sync_command()
        return data

    def needs_venv(self) -> bool:
        return True

    def sync_is_exact(self, session: Session) -> bool:  # noqa: ARG002
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
    """The ``nox.env`` namespace of environment types."""

    standard = Environment
    pylock = PylockEnvironment
    uv_project = UvProjectEnvironment


env = _EnvAPI()
