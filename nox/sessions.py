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
import enum
import hashlib
import os
import re
import sys
import unicodedata
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import nox.command
import py
from nox import _typing
from nox._decorators import Func
from nox.logger import logger
from nox.virtualenv import CondaEnv, PassthroughEnv, ProcessEnv, VirtualEnv

if _typing.TYPE_CHECKING:
    from nox.manifest import Manifest


def _normalize_path(envdir: str, path: Union[str, bytes]) -> str:
    """Normalizes a string to be a "safe" filesystem path for a virtualenv."""
    if isinstance(path, bytes):
        path = path.decode("utf-8")

    path = unicodedata.normalize("NFKD", path).encode("ascii", "ignore")
    path = path.decode("ascii")
    path = re.sub(r"[^\w\s-]", "-", path).strip().lower()
    path = re.sub(r"[-\s]+", "-", path)
    path = path.strip("-")

    full_path = os.path.join(envdir, path)
    if len(full_path) > 100 - len("bin/pythonX.Y"):
        if len(envdir) < 100 - 9:
            path = hashlib.sha1(path.encode("ascii")).hexdigest()[:8]
            full_path = os.path.join(envdir, path)
            logger.warning("The virtualenv name was hashed to avoid being too long.")
        else:
            logger.error(
                "The virtualenv path {} is too long and will cause issues on "
                "some environments. Use the --envdir path to modify where "
                "nox stores virtualenvs.".format(full_path)
            )

    return full_path


def _dblquote_pkg_install_args(args: Tuple[str, ...]) -> Tuple[str, ...]:
    """Double-quote package install arguments in case they contain '>' or '<' symbols"""

    # routine used to handle a single arg
    def _dblquote_pkg_install_arg(pkg_req_str: str) -> str:
        # sanity check: we need an even number of double-quotes
        if pkg_req_str.count('"') % 2 != 0:
            raise ValueError(
                "ill-formated argument with odd number of quotes: %s" % pkg_req_str
            )

        if "<" in pkg_req_str or ">" in pkg_req_str:
            if pkg_req_str[0] == '"' and pkg_req_str[-1] == '"':
                # already double-quoted string
                return pkg_req_str
            else:
                # need to double-quote string
                if '"' in pkg_req_str:
                    raise ValueError(
                        "Cannot escape requirement string: %s" % pkg_req_str
                    )
                return '"%s"' % pkg_req_str
        else:
            # no dangerous char: no need to double-quote string
            return pkg_req_str

    # double-quote all args that need to be and return the result
    return tuple(_dblquote_pkg_install_arg(a) for a in args)


class _SessionQuit(Exception):
    pass


class _SessionSkip(Exception):
    pass


class Status(enum.Enum):
    ABORTED = -1
    FAILED = 0
    SUCCESS = 1
    SKIPPED = 2


class Session:
    """The Session object is passed into each user-defined session function.

    This is your primary means for installing package and running commands in
    your Nox session.
    """

    __slots__ = ("_runner",)

    def __init__(self, runner: "SessionRunner") -> None:
        self._runner = runner

    @property
    def __dict__(self) -> "Dict[str, SessionRunner]":  # type: ignore
        """Attribute dictionary for object inspection.

        This is needed because ``__slots__`` turns off ``__dict__`` by
        default. Unlike a typical object, modifying the result of this
        dictionary won't allow modification of the instance.
        """
        return {"_runner": self._runner}

    @property
    def name(self) -> str:
        """The name of this session."""
        return self._runner.friendly_name

    @property
    def env(self) -> dict:
        """A dictionary of environment variables to pass into all commands."""
        return self.virtualenv.env

    @property
    def posargs(self) -> List[str]:
        """This is set to any extra arguments
        passed to ``nox`` on the commandline."""
        return self._runner.global_config.posargs

    @property
    def virtualenv(self) -> ProcessEnv:
        """The virtualenv that all commands are run in."""
        venv = self._runner.venv
        if venv is None:
            raise ValueError("A virtualenv has not been created for this session")
        return venv

    @property
    def python(self) -> Optional[Union[str, Sequence[str], bool]]:
        """The python version passed into ``@nox.session``."""
        return self._runner.func.python

    @property
    def bin_paths(self) -> Optional[List[str]]:
        """The bin directories for the virtualenv."""
        return self.virtualenv.bin_paths

    @property
    def bin(self) -> str:
        """The first bin directory for the virtualenv."""
        paths = self.bin_paths
        if paths is None:
            raise ValueError("The environment does not have a bin directory.")
        return paths[0]

    def create_tmp(self) -> str:
        """Create, and return, a temporary directory."""
        tmpdir = os.path.join(self._runner.envdir, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.env["TMPDIR"] = tmpdir
        return tmpdir

    @property
    def interactive(self) -> bool:
        """Returns True if Nox is being run in an interactive session or False otherwise."""
        return not self._runner.global_config.non_interactive and sys.stdin.isatty()

    def chdir(self, dir: Union[str, os.PathLike]) -> None:
        """Change the current working directory."""
        self.log("cd {}".format(dir))
        os.chdir(dir)

    cd = chdir
    """An alias for :meth:`chdir`."""

    def _run_func(
        self, func: Callable, args: Iterable[Any], kwargs: Mapping[str, Any]
    ) -> Any:
        """Legacy support for running a function through :func`run`."""
        self.log("{}(args={!r}, kwargs={!r})".format(func, args, kwargs))
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("Function {!r} raised {!r}.".format(func, e))
            raise nox.command.CommandFailed()

    def run(
        self, *args: str, env: Mapping[str, str] = None, **kwargs: Any
    ) -> Optional[Any]:
        """Run a command.

        Commands must be specified as a list of strings, for example::

            session.run('pytest', '-k', 'fast', 'tests/')
            session.run('flake8', '--import-order-style=google')

        You **can not** just pass everything as one string. For example, this
        **will not work**::

            session.run('pytest -k fast tests/')

        You can set environment variables for the command using ``env``::

            session.run(
                'bash', '-c', 'echo $SOME_ENV',
                env={'SOME_ENV': 'Hello'})

        You can also tell nox to treat non-zero exit codes as success using
        ``success_codes``. For example, if you wanted to treat the ``pytest``
        "tests discovered, but none selected" error as success::

            session.run(
                'pytest', '-k', 'not slow',
                success_codes=[0, 5])

        On Windows, builtin commands like ``del`` cannot be directly invoked,
        but you can use ``cmd /c`` to invoke them::

            session.run('cmd', '/c', 'del', 'docs/modules.rst')

        :param env: A dictionary of environment variables to expose to the
            command. By default, all environment variables are passed.
        :type env: dict or None
        :param bool silent: Silence command output, unless the command fails.
            ``False`` by default.
        :param success_codes: A list of return codes that are considered
            successful. By default, only ``0`` is considered success.
        :type success_codes: list, tuple, or None
        :param external: If False (the default) then programs not in the
            virtualenv path will cause a warning. If True, no warning will be
            emitted. These warnings can be turned into errors using
            ``--error-on-external-run``. This has no effect for sessions that
            do not have a virtualenv.
        :type external: bool
        """
        if not args:
            raise ValueError("At least one argument required to run().")

        if self._runner.global_config.install_only:
            logger.info("Skipping {} run, as --install-only is set.".format(args[0]))
            return None

        return self._run(*args, env=env, **kwargs)

    def run_always(
        self, *args: str, env: Mapping[str, str] = None, **kwargs: Any
    ) -> Optional[Any]:
        """Run a command **always**.

        This is a variant of :meth:`run` that runs in all cases, including in
        the presence of ``--install-only``.

        :param env: A dictionary of environment variables to expose to the
            command. By default, all environment variables are passed.
        :type env: dict or None
        :param bool silent: Silence command output, unless the command fails.
            ``False`` by default.
        :param success_codes: A list of return codes that are considered
            successful. By default, only ``0`` is considered success.
        :type success_codes: list, tuple, or None
        :param external: If False (the default) then programs not in the
            virtualenv path will cause a warning. If True, no warning will be
            emitted. These warnings can be turned into errors using
            ``--error-on-external-run``. This has no effect for sessions that
            do not have a virtualenv.
        :type external: bool
        """
        if not args:
            raise ValueError("At least one argument required to run_always().")

        return self._run(*args, env=env, **kwargs)

    def _run(self, *args: str, env: Mapping[str, str] = None, **kwargs: Any) -> Any:
        """Like run(), except that it runs even if --install-only is provided."""
        # Legacy support - run a function given.
        if callable(args[0]):
            return self._run_func(args[0], args[1:], kwargs)

        # Combine the env argument with our virtualenv's env vars.
        if env is not None:
            overlay_env = env
            env = self.env.copy()
            env.update(overlay_env)
        else:
            env = self.env

        # If --error-on-external-run is specified, error on external programs.
        if self._runner.global_config.error_on_external_run:
            kwargs.setdefault("external", "error")

        # Allow all external programs when running outside a sandbox.
        if not self.virtualenv.is_sandboxed:
            kwargs["external"] = True

        if args[0] in self.virtualenv.allowed_globals:
            kwargs["external"] = True

        # Run a shell command.
        return nox.command.run(args, env=env, paths=self.bin_paths, **kwargs)

    def conda_install(
        self, *args: str, auto_offline: bool = True, **kwargs: Any
    ) -> None:
        """Install invokes `conda install`_ to install packages inside of the
        session's environment.

        To install packages directly::

            session.conda_install('pandas')
            session.conda_install('numpy', 'scipy')
            session.conda_install('--channel=conda-forge', 'dask==2.1.0')

        To install packages from a ``requirements.txt`` file::

            session.conda_install('--file', 'requirements.txt')
            session.conda_install('--file', 'requirements-dev.txt')

        By default this method will detect when internet connection is not
        available and will add the `--offline` flag automatically in that case.
        To disable this behaviour, set `auto_offline=False`.

        To install the current package without clobbering conda-installed
        dependencies::

            session.install('.', '--no-deps')
            # Install in editable mode.
            session.install('-e', '.', '--no-deps')

        Additional keyword args are the same as for :meth:`run`.

        .. _conda install:
        """
        venv = self._runner.venv

        prefix_args = ()  # type: Tuple[str, ...]
        if isinstance(venv, CondaEnv):
            prefix_args = ("--prefix", venv.location)
        elif not isinstance(venv, PassthroughEnv):  # pragma: no cover
            raise ValueError(
                "A session without a conda environment can not install dependencies from conda."
            )

        if not args:
            raise ValueError("At least one argument required to install().")

        # Escape args that should be (conda-specific; pip install does not need this)
        args = _dblquote_pkg_install_args(args)

        if "silent" not in kwargs:
            kwargs["silent"] = True

        extraopts = ()  # type: Tuple[str, ...]
        if auto_offline and venv.is_offline():
            logger.warning(
                "Automatically setting the `--offline` flag as conda repo seems unreachable."
            )
            extraopts = ("--offline",)

        self._run(
            "conda",
            "install",
            "--yes",
            *extraopts,
            *prefix_args,
            *args,
            external="error",
            **kwargs
        )

    def install(self, *args: str, **kwargs: Any) -> None:
        """Install invokes `pip`_ to install packages inside of the session's
        virtualenv.

        To install packages directly::

            session.install('pytest')
            session.install('requests', 'mock')
            session.install('requests[security]==2.9.1')

        To install packages from a ``requirements.txt`` file::

            session.install('-r', 'requirements.txt')
            session.install('-r', 'requirements-dev.txt')

        To install the current package::

            session.install('.')
            # Install in editable mode.
            session.install('-e', '.')

        Additional keyword args are the same as for :meth:`run`.

        .. _pip: https://pip.readthedocs.org
        """
        if not isinstance(
            self._runner.venv, (CondaEnv, VirtualEnv, PassthroughEnv)
        ):  # pragma: no cover
            raise ValueError(
                "A session without a virtualenv can not install dependencies."
            )
        if not args:
            raise ValueError("At least one argument required to install().")

        if "silent" not in kwargs:
            kwargs["silent"] = True

        self._run("python", "-m", "pip", "install", *args, external="error", **kwargs)

    def notify(self, target: "Union[str, SessionRunner]") -> None:
        """Place the given session at the end of the queue.

        This method is idempotent; multiple notifications to the same session
        have no effect.

        Args:
            target (Union[str, Callable]): The session to be notified. This
                may be specified as the appropriate string (same as used for
                ``nox -s``) or using the function object.
        """
        self._runner.manifest.notify(target)

    def log(self, *args: Any, **kwargs: Any) -> None:
        """Outputs a log during the session."""
        logger.info(*args, **kwargs)

    def error(self, *args: Any) -> "_typing.NoReturn":
        """Immediately aborts the session and optionally logs an error."""
        raise _SessionQuit(*args)

    def skip(self, *args: Any) -> "_typing.NoReturn":
        """Immediately skips the session and optionally logs a warning."""
        raise _SessionSkip(*args)


class SessionRunner:
    def __init__(
        self,
        name: str,
        signatures: List[str],
        func: Func,
        global_config: argparse.Namespace,
        manifest: "Manifest",
    ) -> None:
        self.name = name
        self.signatures = signatures
        self.func = func
        self.global_config = global_config
        self.manifest = manifest
        self.venv = None  # type: Optional[ProcessEnv]

    @property
    def description(self) -> Optional[str]:
        doc = self.func.__doc__
        if doc:
            first_line = doc.strip().split("\n")[0]
            return first_line
        return None

    def __str__(self) -> str:
        sigs = ", ".join(self.signatures)
        return "Session(name={}, signatures={})".format(self.name, sigs)

    @property
    def friendly_name(self) -> str:
        return self.signatures[0] if self.signatures else self.name

    @property
    def envdir(self) -> str:
        return _normalize_path(self.global_config.envdir, self.friendly_name)

    def _create_venv(self) -> None:
        backend = (
            self.global_config.force_venv_backend
            or self.func.venv_backend
            or self.global_config.default_venv_backend
        )

        if backend == "none" or self.func.python is False:
            self.venv = PassthroughEnv()
            return

        reuse_existing = (
            self.func.reuse_venv or self.global_config.reuse_existing_virtualenvs
        )

        if backend is None or backend == "virtualenv":
            self.venv = VirtualEnv(
                self.envdir,
                interpreter=self.func.python,  # type: ignore
                reuse_existing=reuse_existing,
                venv_params=self.func.venv_params,
            )
        elif backend == "conda":
            self.venv = CondaEnv(
                self.envdir,
                interpreter=self.func.python,  # type: ignore
                reuse_existing=reuse_existing,
                venv_params=self.func.venv_params,
            )
        elif backend == "venv":
            self.venv = VirtualEnv(
                self.envdir,
                interpreter=self.func.python,  # type: ignore
                reuse_existing=reuse_existing,
                venv=True,
                venv_params=self.func.venv_params,
            )
        else:
            raise ValueError(
                "Expected venv_backend one of ('virtualenv', 'conda', 'venv'), but got '{}'.".format(
                    backend
                )
            )

        self.venv.create()

    def execute(self) -> "Result":
        logger.warning("Running session {}".format(self.friendly_name))

        try:
            # By default, nox should quietly change to the directory where
            # the noxfile.py file is located.
            cwd = py.path.local(
                os.path.realpath(os.path.dirname(self.global_config.noxfile))
            ).as_cwd()

            with cwd:
                self._create_venv()
                session = Session(self)
                self.func(session)

            # Nothing went wrong; return a success.
            return Result(self, Status.SUCCESS)

        except nox.virtualenv.InterpreterNotFound as exc:
            if self.global_config.error_on_missing_interpreters:
                return Result(self, Status.FAILED, reason=str(exc))
            else:
                return Result(self, Status.SKIPPED, reason=str(exc))

        except _SessionQuit as exc:
            return Result(self, Status.ABORTED, reason=str(exc))

        except _SessionSkip as exc:
            return Result(self, Status.SKIPPED, reason=str(exc))

        except nox.command.CommandFailed:
            return Result(self, Status.FAILED)

        except KeyboardInterrupt:
            logger.error("Session {} interrupted.".format(self.friendly_name))
            raise

        except Exception as exc:
            logger.exception(
                "Session {} raised exception {!r}".format(self.friendly_name, exc)
            )
            return Result(self, Status.FAILED)


class Result:
    """An object representing the result of a session."""

    def __init__(
        self, session: SessionRunner, status: Status, reason: Optional[str] = None
    ) -> None:
        """Initialize the Result object.

        Args:
            session (~nox.sessions.SessionRunner):
                The session runner which ran.
            status (~nox.sessions.Status): The final result status.
            reason (str): Additional info.
        """
        self.session = session
        self.status = status
        self.reason = reason

    def __bool__(self) -> bool:
        return self.status.value > 0

    def __nonzero__(self) -> bool:
        return self.__bool__()

    @property
    def imperfect(self) -> str:
        """Return the English imperfect tense for the status.

        Returns:
            str: A word or phrase representing the status.
        """
        if self.status == Status.SUCCESS:
            return "was successful"
        status = self.status.name.lower()
        if self.reason:
            return "{}: {}".format(status, self.reason)
        else:
            return status

    def log(self, message: str) -> None:
        """Log a message using the appropriate log function.

        Args:
            message (str): The message to be logged.
        """
        log_function = logger.info
        if self.status == Status.SUCCESS:
            log_function = logger.success
        if self.status == Status.SKIPPED:
            log_function = logger.warning
        if self.status.value <= 0:
            log_function = logger.error
        log_function(message)

    def serialize(self) -> Dict[str, Any]:
        """Return a serialized representation of this result.

        Returns:
            dict: The serialized result.
        """
        return {
            "args": getattr(self.session.func, "call_spec", {}),
            "name": self.session.name,
            "result": self.status.name.lower(),
            "result_code": self.status.value,
            "signatures": self.session.signatures,
        }
