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

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import TYPE_CHECKING

from nox.sessions import Result, Status, _duration_str
from nox.tasks import _warn_pythons_ignored

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Callable

    from nox.manifest import Manifest
    from nox.sessions import SessionRunner

_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_SYMBOLS = {
    Status.SUCCESS: "✓",
    Status.SKIPPED: "⊘",
    Status.FAILED: "✗",
    Status.ABORTED: "↯",
}
_COLORS = {
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "purple": "\x1b[35m",
    "cyan": "\x1b[36m",
    "grey": "\x1b[90m",
    "bold": "\x1b[1m",
    "reset": "\x1b[0m",
}
_ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def _make_color_formatter(*, color: bool) -> Callable[..., str]:
    """Return a function that wraps text in ANSI codes, or a no-op if disabled."""
    if not color:
        return lambda text, *codes: text

    def colorize(text: str, *codes: str) -> str:
        return "".join(_COLORS[code] for code in codes) + text + _COLORS["reset"]

    return colorize


def _preview_text(line: str) -> str:
    """Turn a raw output line into a one-line, plain-text status preview.

    Keeps only what follows the last carriage return (so progress-bar redraws
    show their latest state) and strips ANSI escapes so truncation can't split
    an escape sequence and corrupt the terminal.
    """
    return _ANSI.sub("", line.rstrip("\n").rsplit("\r", 1)[-1]).strip()


class _Reporter:
    """Buffers per-session output and renders progress.

    On a TTY a background thread redraws a live status board of the running
    sessions; otherwise plain start/finish lines are printed. Either way, each
    session's full output is flushed as one block when it finishes.
    """

    def __init__(self, *, color: bool, tty: bool, total: int = 0) -> None:
        self.color = color
        self.tty = tty
        self.stream = sys.stdout
        self._lock = threading.RLock()
        self._total = total
        self._passed = 0
        self._failed = 0
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

        _c = _make_color_formatter(color=self.color)
        running = len(self._active)
        done = self._passed + self._failed
        queued = max(0, self._total - done - running)
        header = (
            f"{_c('nox > --parallel:', 'bold', 'purple')} "
            f"{_c('running', 'blue')} {running} · "
            f"{_c('passed', 'green')} {self._passed} · "
            f"{_c('failed', 'red')} {self._failed} · "
            f"{_c('queued', 'yellow')} {queued}"
        )
        plain_header = _ANSI.sub("", header)
        if width and len(plain_header) > width - 1:
            # Too narrow for the styled header; truncate the plain text instead.
            header = plain_header[: width - 1]
        lines = [header]

        frame = _SPINNER[self._spin % len(_SPINNER)]
        for name, start in self._active.items():
            head = f"{frame} {name} ({int(now - start)}s)"
            if width and len(head) > width - 1:
                # Too narrow even for the header; fall back to plain truncation.
                lines.append(head[: width - 1])
                continue
            preview = self._preview.get(name, "")
            if preview and width:
                budget = width - 1 - len(head) - 2  # 2 for the separating spaces
                preview = preview[:budget] if budget > 0 else ""
            line = (
                f"{_c(frame, 'cyan')} "
                f"{_c(name, 'bold', 'cyan')} "
                f"{_c(f'({int(now - start)}s)', 'green')}"
            )
            if preview:
                line += f"  {_c(preview, 'grey')}"
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
            if result:
                self._passed += 1
            else:
                self._failed += 1
            self._clear_board()
            self._emit_block(name, result, output)
            if self.tty:  # pragma: no cover - requires a live TTY
                self._draw_board()

    def aborted(self, name: str, result: Result) -> None:
        with self._lock:
            self._failed += 1
            self._clear_board()
            self._emit_block(name, result, "")
            if self.tty:  # pragma: no cover - requires a live TTY
                self._draw_board()


def _child_argv(
    global_config: Namespace, session: SessionRunner, report_path: str
) -> list[str]:
    """Build the ``nox`` command line that runs a single session in a child."""
    g = global_config
    argv = [
        sys.executable,
        "-m",
        "nox",
        "--noxfile",
        str(g.noxfile),
        "-s",
        session.friendly_name,
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
        status = Status[entry["result"].upper()]
        return Result(
            session, status, entry.get("reason"), duration=entry.get("duration", 0.0)
        )
    except (OSError, ValueError, KeyError, IndexError):
        # The child died before writing a usable report; trust its exit code.
        status = Status.SUCCESS if returncode == 0 else Status.FAILED
        return Result(session, status)


def _run_session(
    session: SessionRunner,
    global_config: Namespace,
    procs: set[subprocess.Popen[str]],
    procs_lock: threading.Lock,
    on_line: Callable[[str], None] | None = None,
) -> tuple[Result, str]:
    """Run a single session in a subprocess; return its result and output.

    Output is read line by line so ``on_line`` (if given) sees each line as it
    arrives, letting the caller show a live preview while the session runs.
    """
    lines: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        report_path = os.path.join(tmp, "report.json")
        # The context manager waits for the process and closes its pipes.
        with subprocess.Popen(
            _child_argv(global_config, session, report_path),
            cwd=getattr(global_config, "invoked_from", None),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="backslashreplace",
        ) as proc:
            with procs_lock:
                procs.add(proc)
            try:
                assert proc.stdout is not None
                for line in iter(proc.stdout.readline, ""):
                    lines.append(line)
                    if on_line is not None:
                        on_line(line)
            finally:
                with procs_lock:
                    procs.discard(proc)
        return _read_report(report_path, session, proc.returncode), "".join(lines)


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
    for session in queue:
        _warn_pythons_ignored(session)

    in_queue = set(queue)
    deps: dict[SessionRunner, list[SessionRunner]] = {
        session: [d for d in session.get_direct_dependencies() if d in in_queue]
        for session in queue
    }

    results: dict[SessionRunner, Result] = {}
    not_started = list(queue)
    futures: dict[Future[Result], SessionRunner] = {}
    procs: set[subprocess.Popen[str]] = set()
    procs_lock = threading.Lock()
    stop = False

    reporter = _Reporter(
        color=bool(getattr(global_config, "color", False)),
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
            on_line=lambda line: reporter.update(name, line),
        )
        reporter.finished(name, result, output)
        return result

    start = time.monotonic()
    with reporter, ThreadPoolExecutor(max_workers=jobs) as executor:
        try:
            while True:
                if not stop:
                    _schedule_ready(
                        not_started,
                        deps,
                        results,
                        reporter,
                        executor,
                        worker,
                        futures,
                        jobs,
                    )
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
                for proc in procs:
                    proc.terminate()
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    # Report wall-clock time in the summary, not the sum of session durations.
    global_config.parallel_wall_time = time.monotonic() - start
    return [results[session] for session in queue if session in results]


def _schedule_ready(
    not_started: list[SessionRunner],
    deps: dict[SessionRunner, list[SessionRunner]],
    results: dict[SessionRunner, Result],
    reporter: _Reporter,
    executor: ThreadPoolExecutor,
    worker: Callable[[SessionRunner], Result],
    futures: dict[Future[Result], SessionRunner],
    jobs: int,
) -> None:
    """Submit ready sessions, up to ``jobs`` running at once.

    A session is ready once all its dependencies have completed. Sessions with
    a failed/aborted/skipped prerequisite are aborted in place (without spawning
    a subprocess and regardless of capacity), which cascades down the graph.
    """
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
                reporter.aborted(session.friendly_name, result)
            elif len(futures) < jobs:
                not_started.remove(session)
                progressed = True
                futures[executor.submit(worker, session)] = session
