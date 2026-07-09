# Copyright 2024 Alethea Katherine Flowers
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

"""Parallel session execution.

Each ready session is run in its own ``nox`` subprocess (``--no-dependencies``,
``--parallel 1``), with its output buffered and printed as a contiguous block
when it finishes (tox-style). The parent process schedules sessions according to
their ``requires=`` dependency graph and never executes a session itself.
"""

from __future__ import annotations

__lazy_modules__ = {
    "colorlog",
    "colorlog.escape_codes",
    "contextlib",
    "io",
    "json",
    "shutil",
    "signal",
    "subprocess",
    "tempfile",
    "threading",
}

import contextlib
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import TYPE_CHECKING

from colorlog.escape_codes import parse_colors

from nox.sessions import Result, Status, _duration_str

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Callable, Collection

    from nox.manifest import Manifest
    from nox.sessions import SessionRunner

_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_SYMBOLS = {
    Status.SUCCESS: "✓",
    Status.SKIPPED: "⊘",
    Status.FAILED: "✗",
    Status.ABORTED: "↯",
}
_ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

# How long a child gets to exit after SIGTERM before it is SIGKILLed.
_TERMINATE_TIMEOUT = 2.0


def _make_color_formatter(*, color: bool) -> Callable[..., str]:
    """Return a function that wraps text in ANSI codes, or a no-op if disabled."""
    if not color:
        return lambda text, *codes: text

    def colorize(text: str, *codes: str) -> str:
        return (
            "".join(parse_colors(code) for code in codes) + text + parse_colors("reset")
        )

    return colorize


def _preview_text(line: str) -> str:
    """Turn a raw output line into a one-line, plain-text status preview.

    Keeps only what follows the last carriage return (so progress-bar redraws
    show their latest state) and strips ANSI escapes so truncation can't split
    an escape sequence and corrupt the terminal.
    """
    return _ANSI.sub("", line.rstrip("\r\n").rsplit("\r", 1)[-1]).strip()


class _Reporter:
    """Buffers per-session output and renders progress.

    On a TTY a background thread redraws a live status board of the running
    sessions; otherwise plain start/finish lines are printed. Either way, each
    session's full output is flushed as one block when it finishes.
    """

    def __init__(self, *, color: bool, tty: bool, total: int = 0) -> None:
        self._c = _make_color_formatter(color=color)
        self.tty = tty
        self.stream = sys.stdout
        self._lock = threading.RLock()
        self._total = total
        self._passed = 0
        self._failed = 0
        self._skipped = 0
        self._active: dict[str, float] = {}
        self._preview: dict[str, str] = {}
        self._board_lines = 0
        self._spin = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> _Reporter:  # noqa: PYI034
        if self.tty:  # pragma: no cover - requires a live TTY
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        if self._thread is not None:  # pragma: no cover - requires a live TTY
            self._thread.join()
        with self._lock:
            self._clear_board()

    def _render(self, now: float, width: int) -> list[str]:
        """Return the status-board lines for the currently-running sessions.

        Each line is the spinner, session name, and elapsed time, followed by a
        preview of the session's latest output line, truncated to ``width``.
        """
        if not self._active:
            return []

        _c = self._c
        running = len(self._active)
        done = self._passed + self._failed + self._skipped
        queued = max(0, self._total - done - running)
        header = (
            f"{_c('nox > --parallel:', 'bold', 'purple')} "
            f"{_c('running', 'blue')} {running} · "
            f"{_c('passed', 'green')} {self._passed} · "
            f"{_c('failed', 'red')} {self._failed} · "
            f"{_c('queued', 'yellow')} {queued}"
        )
        if self._skipped:
            header += f" · {_c('skipped', 'light_black')} {self._skipped}"
        plain_header = _ANSI.sub("", header)
        if width and len(plain_header) > width - 1:
            # Too narrow for the styled header; truncate the plain text instead.
            header = plain_header[: width - 1]
        lines = [header]

        frame = _SPINNER[self._spin % len(_SPINNER)]
        for name, start in self._active.items():
            # Plain and colored renderings are built from the same segments so
            # the width math can't drift from what is actually displayed.
            segments = [
                (frame, ("cyan",)),
                (name, ("bold", "cyan")),
                (f"({int(now - start)}s)", ("green",)),
            ]
            head = " ".join(text for text, _ in segments)
            if width and len(head) > width - 1:
                # Too narrow even for the session line; plain truncation.
                lines.append(head[: width - 1])
                continue
            preview = self._preview.get(name, "")
            if preview and width:
                budget = width - 1 - len(head) - 2  # 2 for the separating spaces
                preview = preview[:budget] if budget > 0 else ""
            line = " ".join(_c(text, *codes) for text, codes in segments)
            if preview:
                line += f"  {_c(preview, 'light_black')}"
            lines.append(line)
        return lines

    def _run(self) -> None:  # pragma: no cover - timing/terminal loop
        while not self._stop.wait(0.25):
            with self._lock:
                self._spin += 1
                self._draw_board()

    def _draw_board(self) -> None:  # pragma: no cover - requires a live TTY
        self._clear_board()
        width = shutil.get_terminal_size().columns
        lines = self._render(time.monotonic(), width)
        for line in lines:
            self.stream.write(line + "\n")
        self.stream.flush()
        self._board_lines = len(lines)

    def _clear_board(self) -> None:
        if self._board_lines:  # pragma: no cover - requires a live TTY
            self.stream.write(f"\x1b[{self._board_lines}A\x1b[J")
            self.stream.flush()
            self._board_lines = 0

    def _emit_block(self, name: str, result: Result, output: str) -> None:
        symbol = _SYMBOLS[result.status]
        duration = _duration_str(result.duration, ", {time}")
        rule = "=" * 10
        self.stream.write(
            f"{rule} {symbol} {name}: {result.status.name.lower()}{duration} {rule}\n"
        )
        if output:
            self.stream.write(output if output.endswith("\n") else output + "\n")
        elif result.reason:
            self.stream.write(f"  {result.reason}\n")
        self.stream.flush()

    def started(self, name: str) -> None:
        with self._lock:
            self._active[name] = time.monotonic()
            if self.tty:  # pragma: no cover - requires a live TTY
                self._draw_board()
            else:
                self.stream.write(f"Starting session {name}...\n")
                self.stream.flush()

    def update(self, name: str, line: str) -> None:
        """Record a session's latest output line for the status-board preview."""
        preview = _preview_text(line)
        if preview:
            with self._lock:
                self._preview[name] = preview

    def finished(self, name: str, result: Result, output: str) -> None:
        with self._lock:
            self._active.pop(name, None)
            self._preview.pop(name, None)
            if result.status is Status.SKIPPED:
                self._skipped += 1
            elif result:
                self._passed += 1
            else:
                self._failed += 1
            self._clear_board()
            self._emit_block(name, result, output)
            if self.tty:  # pragma: no cover - requires a live TTY
                self._draw_board()


def _session_selector(session: SessionRunner) -> str:
    """Return an unambiguous ``-s`` value selecting exactly this session.

    ``friendly_name`` can be shared by several runners: with ``--force-python``,
    parametrized sessions for different interpreters all get e.g. ``test(x=1)``
    as their first signature. The fully-qualified signature (name, interpreter,
    and parameters, e.g. ``test-3.10(x=1)``) is unique, and is always the
    longest one a runner has.
    """
    return max(session.signatures, key=len) if session.signatures else session.name


def _child_argv(
    global_config: Namespace, session: SessionRunner, report_path: str
) -> list[str]:
    """Build the ``nox`` command line that runs a single session in a child.

    Every global option that affects how a session executes must be forwarded
    here, or parallel runs will silently diverge from sequential ones — keep
    this in sync when adding options.
    """
    g = global_config
    argv = [
        sys.executable,
        "-m",
        "nox",
        "--noxfile",
        str(g.noxfile),
        "-s",
        _session_selector(session),
        "--no-dependencies",
        "--parallel",
        "1",
        "--report",
        report_path,
    ]
    if g.envdir:
        argv += ["--envdir", str(g.envdir)]
    if g.reuse_venv:
        argv += ["--reuse-venv", str(g.reuse_venv)]
    if g.no_install:
        argv.append("--no-install")
    if g.install_only:
        argv.append("--install-only")
    # The "uv|virtualenv" fallback syntax is only valid in the Noxfile, not on
    # the command line (which validates against single backends). The child
    # re-reads the Noxfile, so only forward a backend that names a single one;
    # a fallback expression is re-derived from the Noxfile by the child.
    if g.default_venv_backend and "|" not in g.default_venv_backend:
        argv += ["--default-venv-backend", str(g.default_venv_backend)]
    if g.force_venv_backend and "|" not in g.force_venv_backend:
        argv += ["--force-venv-backend", str(g.force_venv_backend)]
    if g.download_python:
        argv += ["--download-python", str(g.download_python)]
    # Reproduce the parent's interpreter selection so the child rebuilds the
    # same manifest; otherwise forced/extra-python signatures (e.g. tests-3.12)
    # don't exist in the child and it fails with "Sessions not found".
    if g.force_pythons:
        argv += ["--force-python", *g.force_pythons]
    if g.extra_pythons:
        argv += ["--extra-python", *g.extra_pythons]
    if g.pythons:
        argv += ["--python", *g.pythons]
    argv.append(
        "--error-on-missing-interpreters"
        if g.error_on_missing_interpreters
        else "--no-error-on-missing-interpreters"
    )
    argv.append(
        "--error-on-external-run"
        if g.error_on_external_run
        else "--no-error-on-external-run"
    )
    if g.non_interactive:
        argv.append("--non-interactive")
    if g.add_timestamp:
        argv.append("--add-timestamp")
    if g.verbose:
        argv.append("-v")
    argv.append("--forcecolor" if g.color else "--nocolor")
    if g.posargs:
        argv.append("--")
        argv.extend(g.posargs)
    return argv


def _read_report(path: str, session: SessionRunner, returncode: int) -> Result:
    """Reconstruct a ``Result`` from a child's ``--report`` file."""
    try:
        with open(path, encoding="utf-8") as report_file:
            entry = json.load(report_file)["sessions"][0]
        duration = entry.get("duration", 0.0)
        status = Status[entry["result"].upper()]
        result = Result(session, status, entry.get("reason"), duration=duration)
    except (OSError, ValueError, KeyError, IndexError):
        # The child died before writing a usable report; trust its exit code.
        status = Status.SUCCESS if returncode == 0 else Status.FAILED
        return Result(session, status)
    # A child may run more than the scheduled session (e.g. via notify()); its
    # exit code reflects every one of them. Don't report success over a non-zero
    # child whose first session happened to pass.
    if returncode != 0 and result:
        return Result(session, Status.FAILED, duration=duration)
    return result


def _run_session(
    session: SessionRunner,
    global_config: Namespace,
    procs: set[subprocess.Popen[bytes]],
    procs_lock: threading.Lock,
    on_line: Callable[[str], None] | None = None,
) -> tuple[Result, str]:
    """Run a single session in a subprocess; return its result and output.

    Output is read line by line so ``on_line`` (if given) sees each line as it
    arrives, letting the caller show a live preview while the session runs. It
    is spooled to a temporary file rather than held in memory, so a
    long-running verbose session only occupies RAM briefly when it finishes.
    """
    with tempfile.TemporaryDirectory() as tmp:
        report_path = os.path.join(tmp, "report.json")
        output_path = os.path.join(tmp, "output.txt")
        # The context manager waits for the process and closes its pipes.
        with (
            subprocess.Popen(
                _child_argv(global_config, session, report_path),
                cwd=global_config.invoked_from,
                # Detach stdin so the child never sees a TTY: parallel sessions
                # must not prompt or read from the shared terminal (they would
                # race/hang).
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                # Own process group (POSIX) so an interrupt can stop the whole
                # tree, including the session's own subprocesses.
                start_new_session=(os.name == "posix"),
            ) as proc,
            open(output_path, "w", encoding="utf-8", newline="") as spool,
        ):
            with procs_lock:
                procs.add(proc)
            try:
                assert proc.stdout is not None
                # newline="" splits at \r too but doesn't translate it, so
                # progress-bar redraws stay overwrites instead of becoming
                # separate lines in the buffered block.
                reader = io.TextIOWrapper(
                    proc.stdout,
                    encoding="utf-8",
                    errors="backslashreplace",
                    newline="",
                )
                for raw_line in iter(reader.readline, ""):
                    line = (
                        f"{raw_line[:-2]}\n" if raw_line.endswith("\r\n") else raw_line
                    )
                    spool.write(line)
                    if on_line is not None:
                        on_line(line)
            finally:
                with procs_lock:
                    procs.discard(proc)
        with open(output_path, encoding="utf-8", newline="") as spool:
            output = spool.read()
        return _read_report(report_path, session, proc.returncode), output


def _signal_group(proc: subprocess.Popen[bytes], *, kill: bool) -> None:
    """Signal a child's whole process group (POSIX), or just the child."""
    if os.name == "posix":
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL if kill else signal.SIGTERM)
        return
    (proc.kill if kill else proc.terminate)()  # pragma: no cover - Windows


def _stop_procs(procs: Collection[subprocess.Popen[bytes]]) -> None:
    """Terminate the children (and their process groups, so the sessions' own
    subprocesses stop too), escalating to SIGKILL for any that don't exit."""
    for proc in procs:
        _signal_group(proc, kill=False)
    deadline = time.monotonic() + _TERMINATE_TIMEOUT
    for proc in procs:
        try:
            proc.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:  # noqa: PERF203 - cold shutdown path
            _signal_group(proc, kill=True)


def run_manifest_parallel(
    manifest: Manifest, global_config: Namespace, jobs: int
) -> list[Result]:
    """Run the manifest's sessions concurrently, honoring ``requires=``.

    Args:
        manifest: The (already filtered and dependency-resolved) manifest.
        global_config: The global configuration.
        jobs: The maximum number of sessions to run at once.

    Returns:
        The results, in manifest order, for every session that ran.
    """
    queue = list(manifest)
    in_queue = set(queue)
    deps: dict[SessionRunner, list[SessionRunner]] = {
        session: [d for d in session.get_direct_dependencies() if d in in_queue]
        for session in queue
    }

    results: dict[SessionRunner, Result] = {}
    not_started = list(queue)
    futures: dict[Future[Result], SessionRunner] = {}
    procs: set[subprocess.Popen[bytes]] = set()
    procs_lock = threading.Lock()
    stop = False

    reporter = _Reporter(
        color=bool(global_config.color),
        tty=sys.stdout.isatty(),
        total=len(queue),
    )

    def worker(session: SessionRunner) -> Result:
        name = session.friendly_name
        reporter.started(name)
        result, output = _run_session(
            session,
            global_config,
            procs,
            procs_lock,
            # The preview only feeds the TTY status board; skip the per-line
            # work entirely when there isn't one.
            on_line=(lambda line: reporter.update(name, line))
            if reporter.tty
            else None,
        )
        reporter.finished(name, result, output)
        return result

    def schedule_ready(executor: ThreadPoolExecutor) -> None:
        """Submit ready sessions, up to ``jobs`` running at once.

        A session is ready once all its dependencies have completed. Sessions
        with a failed/aborted/skipped prerequisite are aborted in place
        (without spawning a subprocess and regardless of capacity), which
        cascades down the graph. Sessions sharing an envdir (runners with
        duplicated friendly names under ``--force-python``) are never run at
        the same time, as they would build the same virtualenv concurrently.
        Sessions that haven't opted in with ``allow_parallel=True`` run
        exclusively: they start only when nothing else is running, and nothing
        starts alongside them.
        """
        busy_envdirs = {running.envdir for running in futures.values()}
        exclusive_running = any(
            not running.func.allow_parallel for running in futures.values()
        )
        # The fixpoint loop is load-bearing: when a failure cascades while
        # nothing is running, every transitive dependent must be aborted in
        # this call, because the main loop exits once no futures remain.
        progressed = True
        while progressed:
            progressed = False
            for session in list(not_started):
                session_deps = deps[session]
                if not all(dep in results for dep in session_deps):
                    continue
                failed = [dep for dep in session_deps if not results[dep]]
                if failed:
                    not_started.remove(session)
                    progressed = True
                    result = Result(
                        session,
                        Status.ABORTED,
                        reason=(
                            f"Prerequisite session {failed[0].friendly_name} was not"
                            " successful"
                        ),
                        duration=0,
                    )
                    results[session] = result
                    reporter.finished(session.friendly_name, result, "")
                elif (
                    len(futures) < jobs
                    and not exclusive_running
                    and session.envdir not in busy_envdirs
                    and (session.func.allow_parallel or not futures)
                ):
                    not_started.remove(session)
                    progressed = True
                    busy_envdirs.add(session.envdir)
                    exclusive_running = not session.func.allow_parallel
                    futures[executor.submit(worker, session)] = session

    start = time.monotonic()
    with reporter, ThreadPoolExecutor(max_workers=jobs) as executor:
        try:
            while True:
                if not stop:
                    schedule_ready(executor)
                if not futures:
                    break
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    session = futures.pop(future)
                    result = future.result()
                    results[session] = result
                    if not result and global_config.stop_on_first_error:
                        stop = True
        except KeyboardInterrupt:  # pragma: no cover - hard to trigger in tests
            with procs_lock:
                running = list(procs)
            _stop_procs(running)
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    # Report wall-clock time in the summary, not the sum of session durations.
    global_config.parallel_wall_time = time.monotonic() - start
    return [results[session] for session in queue if session in results]
