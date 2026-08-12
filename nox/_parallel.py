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
    "copy",
    "io",
    "json",
    "shutil",
    "signal",
    "subprocess",
    "tempfile",
    "threading",
}

import contextlib
import copy
import dataclasses
import functools
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

from nox import _option_set
from nox.sessions import Result, Status, _duration_str, resolve_allow_parallel

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterator

    from nox._options import NoxConfig
    from nox.manifest import Manifest
    from nox.sessions import SessionRunner

_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_ASCII_SPINNER = "|/-\\"
_SYMBOLS = {
    Status.SUCCESS: "✓",
    Status.SKIPPED: "⊘",
    Status.FAILED: "✗",
    Status.ABORTED: "↯",
}
_ASCII_SYMBOLS = {
    Status.SUCCESS: "+",
    Status.SKIPPED: "-",
    Status.FAILED: "x",
    Status.ABORTED: "!",
}
_ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

# How long a child gets to exit after SIGTERM before it is SIGKILLed.
_TERMINATE_TIMEOUT = 2.0

_EXPERIMENTAL = "--parallel is experimental — looking for feedback!"


@functools.cache
def _parse_colors(code: str) -> str:
    # The status board re-renders the same handful of codes 4x/second;
    # parse each one once.
    return parse_colors(code)


@dataclasses.dataclass(frozen=True)
class _Colorizer:
    """Wraps text in ANSI codes, or returns it unchanged if color is disabled."""

    color: bool

    def __call__(self, text: str, *codes: str) -> str:
        if not self.color:
            return text
        return (
            "".join(_parse_colors(code) for code in codes)
            + text
            + _parse_colors("reset")
        )


def _preview_text(line: str) -> str:
    """Turn a raw output line into a one-line, plain-text status preview.

    Keeps only what follows the last carriage return (so progress-bar redraws
    show their latest state) and strips ANSI escapes so truncation can't split
    an escape sequence and corrupt the terminal.
    """
    return _ANSI.sub("", line.rstrip("\r\n").rsplit("\r", 1)[-1]).strip()


def _status_symbol(status: Status, encoding: str | None) -> str:
    symbol = _SYMBOLS[status]
    try:
        symbol.encode(encoding or "utf-8")
    except UnicodeEncodeError:
        return _ASCII_SYMBOLS[status]
    return symbol


def _spinner_frame(spin: int, encoding: str | None) -> str:
    frame = _SPINNER[spin % len(_SPINNER)]
    try:
        frame.encode(encoding or "utf-8")
    except UnicodeEncodeError:
        return _ASCII_SPINNER[spin % len(_ASCII_SPINNER)]
    return frame


@dataclasses.dataclass(kw_only=True)
class _Reporter:
    """Buffers per-session output and renders progress.

    On a TTY a background thread redraws a live status board of the running
    sessions; otherwise plain start/finish lines are printed. Either way, each
    session's full output is flushed as one block when it finishes.
    """

    color: bool
    tty: bool
    total: int = 0

    def __post_init__(self) -> None:
        self._c = _Colorizer(self.color)
        self.stream = sys.stdout
        self._lock = threading.RLock()
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
        else:
            # No live board to carry the banner; print it once instead.
            self.stream.write(self._banner() + "\n")
            self.stream.flush()
        return self

    def _banner(self, width: int = 0) -> str:
        if width and len(_EXPERIMENTAL) + 2 > width - 1:
            return _EXPERIMENTAL[: width - 1]
        return self._c(f" {_EXPERIMENTAL} ", "bg_yellow", "black")

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
        queued = max(0, self.total - done - running)
        header = (
            f"{_c('nox > --parallel:', 'bold', 'purple')} "
            f"{_c('running', 'blue')} {running} · "
            f"{_c('passed', 'green')} {self._passed} · "
            f"{_c('failed', 'red')} {self._failed} · "
            f"{_c('queued', 'yellow')} {queued}"
        )
        if self._skipped:
            header += f" · {_c('skipped', 'thin')} {self._skipped}"
        plain_header = _ANSI.sub("", header)
        if width and len(plain_header) > width - 1:
            # Too narrow for the styled header; truncate the plain text instead.
            header = plain_header[: width - 1]
        lines = [self._banner(width), header]

        frame = _spinner_frame(self._spin, self.stream.encoding)
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
                line += f"  {_c(preview, 'thin')}"
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
        symbol = _status_symbol(result.status, self.stream.encoding)
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


@dataclasses.dataclass(frozen=True, eq=False, kw_only=True)
class _Node:
    """A queued session with everything the scheduler needs to place it.

    ``deps`` holds only the prerequisites that are also in the queue. Every
    field is resolved once, not on each scheduling pass.
    """

    session: SessionRunner
    deps: list[SessionRunner]
    envdir: str
    allow_parallel: bool


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
    global_config: NoxConfig, session: SessionRunner, report_path: str
) -> list[str]:
    """Build the ``nox`` command line that runs a single session in a child.

    The config is serialized back into arguments with ``to_argv``, so every
    option is forwarded by its declared ``Forward`` policy and new options
    reach children without changes here. The copy keeps the parent's value
    provenance (``attrs.evolve`` would reset it, silently dropping explicit
    CLI values that equal a field default); only the child-specific overrides
    (select exactly this session, run it alone, report to a file) are applied
    on top.
    """
    child_config = copy.deepcopy(global_config)
    overrides: dict[str, object] = {
        "sessions": [_session_selector(session)],
        "keywords": None,
        "tags": None,
        "parallel": 1,
        "no_dependencies": True,
        "report": report_path,
    }
    for name, value in overrides.items():
        child_config.set_value(name, value, _option_set.Source.COMMAND_LINE)
    return [sys.executable, "-m", "nox", *_option_set.to_argv(child_config)]


def _read_report(path: str, session: SessionRunner, returncode: int) -> Result:
    """Reconstruct a ``Result`` from a child's ``--report`` file."""
    try:
        with open(path, encoding="utf-8") as report_file:
            entry = json.load(report_file)["sessions"][0]
        result = Result.from_dict(session, entry)
    except (OSError, ValueError, KeyError, IndexError):
        # The child died before writing a usable report; trust its exit code.
        status = Status.SUCCESS if returncode == 0 else Status.FAILED
        return Result(session, status)
    # A child may run more than the scheduled session (e.g. via notify()); its
    # exit code reflects every one of them. Don't report success over a non-zero
    # child whose first session happened to pass.
    if returncode != 0 and result:
        return Result(session, Status.FAILED, duration=result.duration)
    return result


class _Children:
    """The child processes that are running right now.

    Each session's child is registered for as long as it runs, so an interrupt
    in the main thread can stop whatever is running at that moment.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._procs: set[subprocess.Popen[bytes]] = set()

    @contextlib.contextmanager
    def spawn(
        self, argv: list[str], cwd: str | None
    ) -> Iterator[subprocess.Popen[bytes]]:
        """Start a session's child process, tracked for as long as it runs."""
        # The context manager waits for the process and closes its pipes.
        with subprocess.Popen(
            argv,
            cwd=cwd,
            # Detach stdin so the child never sees a TTY: parallel sessions
            # must not prompt or read from the shared terminal (they would
            # race/hang).
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # Own process group (POSIX) so an interrupt can stop the whole
            # tree, including the session's own subprocesses.
            start_new_session=(os.name == "posix"),
        ) as proc:
            with self._lock:
                self._procs.add(proc)
            try:
                yield proc
            finally:
                with self._lock:
                    self._procs.discard(proc)

    def stop_all(self) -> None:
        with self._lock:
            running = list(self._procs)
        _stop_procs(running)


def _run_session(
    session: SessionRunner,
    global_config: NoxConfig,
    children: _Children,
    on_line: Callable[[str], None] | None = None,
) -> tuple[Result, str]:
    """Run a single session in a subprocess; return its result and output.

    Output is read line by line so ``on_line`` (if given) sees each line as it
    arrives, letting the caller show a live preview while the session runs.
    """
    with tempfile.TemporaryDirectory() as tmp:
        report_path = os.path.join(tmp, "report.json")
        lines: list[str] = []
        with children.spawn(
            _child_argv(global_config, session, report_path),
            global_config.invoked_from,
        ) as proc:
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
                line = f"{raw_line[:-2]}\n" if raw_line.endswith("\r\n") else raw_line
                lines.append(line)
                if on_line is not None:
                    on_line(line)
        return _read_report(report_path, session, proc.returncode), "".join(lines)


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
    manifest: Manifest, global_config: NoxConfig, jobs: int
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
    nodes = [
        _Node(
            session=session,
            deps=[d for d in session.get_direct_dependencies() if d in in_queue],
            # envdir is a nontrivial property (path normalization, possibly a
            # hashing warning); compute it once instead of on every pass.
            envdir=session.envdir,
            allow_parallel=resolve_allow_parallel(global_config, session.func),
        )
        for session in queue
    ]

    results: dict[SessionRunner, Result] = {}
    not_started = list(nodes)
    futures: dict[Future[Result], _Node] = {}
    children = _Children()
    stop = False

    reporter = _Reporter(
        color=bool(global_config.color),
        tty=sys.stdout.isatty(),
        total=len(queue),
    )

    def worker(node: _Node) -> Result:
        name = node.session.friendly_name
        reporter.started(name)
        result, output = _run_session(
            node.session,
            global_config,
            children,
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
        Sessions that don't allow parallel execution run exclusively: they
        start only when nothing else is running, and nothing starts alongside
        them.
        """
        busy_envdirs = {running.envdir for running in futures.values()}
        exclusive_running = any(
            not running.allow_parallel for running in futures.values()
        )
        # The fixpoint loop is load-bearing: when a failure cascades while
        # nothing is running, every transitive dependent must be aborted in
        # this call, because the main loop exits once no futures remain.
        progressed = True
        while progressed:
            progressed = False
            for node in list(not_started):
                if not all(dep in results for dep in node.deps):
                    continue
                failed = [dep for dep in node.deps if not results[dep]]
                if failed:
                    not_started.remove(node)
                    progressed = True
                    result = Result.aborted_prerequisite(node.session, failed[0])
                    results[node.session] = result
                    reporter.finished(node.session.friendly_name, result, "")
                elif (
                    len(futures) < jobs
                    and not exclusive_running
                    and node.envdir not in busy_envdirs
                    and (node.allow_parallel or not futures)
                ):
                    not_started.remove(node)
                    progressed = True
                    busy_envdirs.add(node.envdir)
                    exclusive_running = not node.allow_parallel
                    futures[executor.submit(worker, node)] = node

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
                    node = futures.pop(future)
                    result = future.result()
                    results[node.session] = result
                    if not result and global_config.stop_on_first_error:
                        stop = True
        except KeyboardInterrupt:  # pragma: no cover - hard to trigger in tests
            children.stop_all()
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    # Report wall-clock time in the summary, not the sum of session durations.
    global_config.parallel_wall_time = time.monotonic() - start
    return [results[session] for session in queue if session in results]
