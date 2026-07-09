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

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import types
import typing
from unittest import mock

import pytest

from nox import _options, _parallel, tasks
from nox.sessions import Result, Session, SessionRunner, Status

if typing.TYPE_CHECKING:
    import argparse
    from collections.abc import Sequence

    from nox.manifest import Manifest


class FakeSession:
    """A minimal stand-in for ``SessionRunner`` for scheduler tests."""

    def __init__(
        self,
        name: str,
        deps: Sequence[FakeSession] = (),
        *,
        allow_parallel: bool = True,
    ) -> None:
        self.friendly_name = name
        self.signatures = [name]
        self.envdir = f".nox/{name}"
        self.func = types.SimpleNamespace(allow_parallel=allow_parallel)
        self._deps = list(deps)

    def get_direct_dependencies(self) -> list[FakeSession]:
        return self._deps


def _fake_runner(session: FakeSession) -> SessionRunner:
    return typing.cast("SessionRunner", session)


def _config(**kwargs: object) -> argparse.Namespace:
    kwargs.setdefault("stop_on_first_error", False)
    return _options.options.namespace(**kwargs)


def _patch_run_session(
    monkeypatch: pytest.MonkeyPatch,
    *,
    failures: Sequence[str] = (),
    calls: list[str] | None = None,
) -> None:
    def fake_run_session(
        session: SessionRunner,
        _global_config: object,
        _procs: object,
        _procs_lock: object,
        **_kwargs: object,
    ) -> tuple[Result, str]:
        if calls is not None:
            calls.append(session.friendly_name)
        status = Status.FAILED if session.friendly_name in failures else Status.SUCCESS
        return Result(
            session, status, duration=0.0
        ), f"output of {session.friendly_name}"

    monkeypatch.setattr(_parallel, "_run_session", fake_run_session)


def _run(sessions: list[FakeSession], config: object, jobs: int = 4) -> list[Result]:
    runners = [_fake_runner(s) for s in sessions]
    return _parallel.run_manifest_parallel(
        typing.cast("Manifest", runners), typing.cast("typing.Any", config), jobs
    )


def test_parallel_all_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_run_session(monkeypatch, calls=calls)
    sessions = [FakeSession(name) for name in ("a", "b", "c")]

    results = _run(sessions, _config(), jobs=3)

    assert [r.status for r in results] == [Status.SUCCESS] * 3
    # Results are returned in queue order regardless of completion order.
    assert [r.session.friendly_name for r in results] == ["a", "b", "c"]
    assert sorted(calls) == ["a", "b", "c"]


def test_parallel_respects_requires_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _patch_run_session(monkeypatch, calls=calls)
    a = FakeSession("a")
    c = FakeSession("c", deps=[a])

    results = _run([a, c], _config(), jobs=4)

    # ``c`` requires ``a``, so it must not start until ``a`` has finished.
    assert calls == ["a", "c"]
    assert all(r.status is Status.SUCCESS for r in results)


def test_parallel_prerequisite_failure_cascades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _patch_run_session(monkeypatch, failures=["d"], calls=calls)
    d = FakeSession("d")
    e = FakeSession("e", deps=[d])

    results = _run([d, e], _config(), jobs=4)

    by_name = {r.session.friendly_name: r for r in results}
    assert by_name["d"].status is Status.FAILED
    assert by_name["e"].status is Status.ABORTED
    assert by_name["e"].reason is not None
    assert "d was not successful" in by_name["e"].reason
    # The aborted session never spawns a subprocess.
    assert "e" not in calls


def test_parallel_stop_on_first_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_run_session(monkeypatch, failures=["x"], calls=calls)
    x = FakeSession("x")
    y = FakeSession("y")

    # jobs=1 forces serial submission, so the failure stops ``y`` from starting.
    results = _run([x, y], _config(stop_on_first_error=True), jobs=1)

    assert calls == ["x"]
    assert [r.session.friendly_name for r in results] == ["x"]


def _patch_run_session_tracking_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, int]:
    """Patch ``_run_session`` with a fake that records peak concurrency.

    The returned dict maps each session's envdir (and the ``"total"`` key) to
    the largest number of simultaneously-running sessions observed. The fake
    sleeps briefly so that sessions submitted together reliably overlap.
    """
    lock = threading.Lock()
    concurrent: dict[str, int] = {}
    peak: dict[str, int] = {}

    def fake_run_session(
        session: SessionRunner,
        _global_config: object,
        _procs: object,
        _procs_lock: object,
        **_kwargs: object,
    ) -> tuple[Result, str]:
        with lock:
            for key in (session.envdir, "total"):
                concurrent[key] = concurrent.get(key, 0) + 1
                peak[key] = max(peak.get(key, 0), concurrent[key])
        time.sleep(0.05)
        with lock:
            for key in (session.envdir, "total"):
                concurrent[key] -= 1
        return Result(session, Status.SUCCESS, duration=0.0), ""

    monkeypatch.setattr(_parallel, "_run_session", fake_run_session)
    return peak


def test_parallel_serializes_shared_envdir(monkeypatch: pytest.MonkeyPatch) -> None:
    # Runners that share an envdir (duplicated friendly names under
    # --force-python) must never run at the same time: the children would
    # create/delete the same virtualenv concurrently and corrupt it.
    peak = _patch_run_session_tracking_concurrency(monkeypatch)
    first, second = FakeSession("test(x=1)"), FakeSession("test(x=1)")

    results = _run([first, second], _config(), jobs=2)

    assert [r.status for r in results] == [Status.SUCCESS] * 2
    assert peak[".nox/test(x=1)"] == 1


def test_parallel_opted_in_sessions_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    peak = _patch_run_session_tracking_concurrency(monkeypatch)
    sessions = [FakeSession("a"), FakeSession("b")]

    results = _run(sessions, _config(), jobs=2)

    assert [r.status for r in results] == [Status.SUCCESS] * 2
    assert peak["total"] == 2


def test_parallel_exclusive_without_allow_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Sessions that don't opt in with allow_parallel=True never run
    # concurrently, even when there is spare capacity.
    peak = _patch_run_session_tracking_concurrency(monkeypatch)
    sessions = [
        FakeSession("a", allow_parallel=False),
        FakeSession("b", allow_parallel=False),
    ]

    results = _run(sessions, _config(), jobs=2)

    assert [r.status for r in results] == [Status.SUCCESS] * 2
    assert peak["total"] == 1


def test_parallel_exclusive_session_runs_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # An exclusive session must not overlap with opted-in sessions either:
    # nothing may be running when it starts, and nothing may start beside it.
    lock = threading.Lock()
    running: set[str] = set()
    overlaps: list[set[str]] = []

    def fake_run_session(
        session: SessionRunner,
        _global_config: object,
        _procs: object,
        _procs_lock: object,
        **_kwargs: object,
    ) -> tuple[Result, str]:
        name = session.friendly_name
        with lock:
            running.add(name)
            if "c" in running and len(running) > 1:
                overlaps.append(set(running))
        time.sleep(0.05)
        with lock:
            running.discard(name)
        return Result(session, Status.SUCCESS, duration=0.0), ""

    monkeypatch.setattr(_parallel, "_run_session", fake_run_session)
    sessions = [
        FakeSession("a"),
        FakeSession("b"),
        FakeSession("c", allow_parallel=False),
        FakeSession("d"),
    ]

    results = _run(sessions, _config(), jobs=4)

    assert [r.status for r in results] == [Status.SUCCESS] * 4
    assert not overlaps


def test_child_argv_full() -> None:
    config = _options.options.namespace(
        noxfile="nf.py",
        envdir="ed",
        reuse_venv="yes",
        no_install=True,
        install_only=True,
        default_venv_backend="uv",
        force_venv_backend="none",
        download_python="auto",
        error_on_missing_interpreters=True,
        error_on_external_run=True,
        non_interactive=True,
        verbose=True,
        color=True,
        add_timestamp=True,
        posargs=["-k", "foo"],
    )
    argv = _parallel._child_argv(
        typing.cast("typing.Any", config),
        _fake_runner(FakeSession("tests-3.12")),
        "report.json",
    )

    assert argv[:3] == [sys.executable, "-m", "nox"]
    assert "--no-dependencies" in argv
    assert argv[argv.index("-s") + 1] == "tests-3.12"
    assert argv[argv.index("--parallel") + 1] == "1"
    assert argv[argv.index("--report") + 1] == "report.json"
    assert argv[argv.index("--noxfile") + 1] == "nf.py"
    assert argv[argv.index("--envdir") + 1] == "ed"
    assert argv[argv.index("--reuse-venv") + 1] == "yes"
    assert "--no-install" in argv
    assert "--install-only" in argv
    assert argv[argv.index("--default-venv-backend") + 1] == "uv"
    assert argv[argv.index("--force-venv-backend") + 1] == "none"
    assert argv[argv.index("--download-python") + 1] == "auto"
    assert "--error-on-missing-interpreters" in argv
    assert "--error-on-external-run" in argv
    assert "--non-interactive" in argv
    assert "-v" in argv
    assert "--forcecolor" in argv
    assert "--add-timestamp" in argv
    assert argv[-3:] == ["--", "-k", "foo"]


def test_child_argv_uses_unique_signature() -> None:
    # With --force-python, parametrized runners for different interpreters
    # share the friendly name (e.g. "test(x=1)" for both 3.10 and 3.11), so
    # -s must use the fully-qualified signature or the child runs them all.
    session = FakeSession("test(x=1)")
    session.signatures = ["test(x=1)", "test-3.10(x=1)", "test-3.10"]
    config = _options.options.namespace(
        noxfile="noxfile.py",
        error_on_missing_interpreters=False,
        error_on_external_run=False,
        color=False,
        posargs=[],
    )
    argv = _parallel._child_argv(
        typing.cast("typing.Any", config), _fake_runner(session), "r.json"
    )
    assert argv[argv.index("-s") + 1] == "test-3.10(x=1)"


def test_child_argv_forwards_python_selection() -> None:
    # Forced/extra/filtered interpreters must reach the child so it rebuilds the
    # same manifest (e.g. the scheduled "tests-3.12" signature exists there too).
    config = _options.options.namespace(
        noxfile="noxfile.py",
        force_pythons=["3.12"],
        extra_pythons=["3.13"],
        pythons=["3.12"],
        error_on_missing_interpreters=False,
        error_on_external_run=False,
        color=False,
        posargs=[],
    )
    argv = _parallel._child_argv(
        typing.cast("typing.Any", config),
        _fake_runner(FakeSession("tests-3.12")),
        "r.json",
    )
    assert argv[argv.index("--force-python") + 1] == "3.12"
    assert argv[argv.index("--extra-python") + 1] == "3.13"
    assert argv[argv.index("--python") + 1] == "3.12"


def test_child_argv_minimal() -> None:
    config = _options.options.namespace(
        noxfile="noxfile.py",
        error_on_missing_interpreters=False,
        error_on_external_run=False,
        color=False,
        posargs=[],
    )
    argv = _parallel._child_argv(
        typing.cast("typing.Any", config),
        _fake_runner(FakeSession("lint")),
        "r.json",
    )

    assert "--no-error-on-missing-interpreters" in argv
    assert "--no-error-on-external-run" in argv
    assert "--nocolor" in argv
    assert "--" not in argv


def test_child_argv_skips_fallback_backend() -> None:
    # The "uv|virtualenv" fallback syntax is Noxfile-only and rejected on the
    # command line, so it must not be forwarded to the child.
    config = _options.options.namespace(
        noxfile="noxfile.py",
        default_venv_backend="uv|virtualenv",
        force_venv_backend="uv|venv",
        error_on_missing_interpreters=False,
        error_on_external_run=False,
        color=False,
        posargs=[],
    )
    argv = _parallel._child_argv(
        typing.cast("typing.Any", config),
        _fake_runner(FakeSession("tests")),
        "r.json",
    )
    assert "--default-venv-backend" not in argv
    assert "--force-venv-backend" not in argv


def _write_report(
    path: str, *, result: str = "success", reason: object = None, duration: float = 1.5
) -> None:
    data = {
        "result": 1,
        "sessions": [
            {
                "name": "x",
                "result": result,
                "result_code": 1,
                "reason": reason,
                "signatures": ["x"],
                "duration": duration,
            }
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def test_read_report_success(tmp_path: object) -> None:
    path = str(tmp_path / "r.json")  # type: ignore[operator]
    _write_report(path, result="success", duration=2.0)
    result = _parallel._read_report(path, _fake_runner(FakeSession("x")), returncode=0)
    assert result.status is Status.SUCCESS
    assert result.duration == 2.0


def test_read_report_skipped_keeps_reason(tmp_path: object) -> None:
    path = str(tmp_path / "r.json")  # type: ignore[operator]
    _write_report(path, result="skipped", reason="no interpreter")
    result = _parallel._read_report(path, _fake_runner(FakeSession("x")), returncode=0)
    assert result.status is Status.SKIPPED
    assert result.reason == "no interpreter"


def test_read_report_nonzero_returncode_overrides_passing_report(
    tmp_path: object,
) -> None:
    # A child that ran an extra notified session may exit non-zero while its
    # first (scheduled) session passed; the failure must not be swallowed.
    path = str(tmp_path / "r.json")  # type: ignore[operator]
    _write_report(path, result="success", duration=3.0)
    result = _parallel._read_report(path, _fake_runner(FakeSession("x")), returncode=1)
    assert result.status is Status.FAILED
    assert result.duration == 3.0


@pytest.mark.parametrize(
    ("returncode", "expected"),
    [(0, Status.SUCCESS), (1, Status.FAILED)],
)
def test_read_report_missing_falls_back_to_returncode(
    tmp_path: object, returncode: int, expected: Status
) -> None:
    path = str(tmp_path / "missing.json")  # type: ignore[operator]
    result = _parallel._read_report(
        path, _fake_runner(FakeSession("x")), returncode=returncode
    )
    assert result.status is expected


def test_reporter_render() -> None:
    reporter = _parallel._Reporter(color=False, tty=False, total=2)
    reporter._active = {"a": 100.0, "b": 100.0}
    reporter._preview = {"a": "compiling module x"}
    lines = reporter._render(105.0, width=0)
    # A summary header, then a line per running session (``a`` has a preview).
    assert lines == [
        "nox > --parallel: running 2 · passed 0 · failed 0 · queued 0",
        "⠋ a (5s)  compiling module x",
        "⠋ b (5s)",
    ]


def test_reporter_render_header_counts() -> None:
    reporter = _parallel._Reporter(color=False, tty=False, total=6)
    reporter._active = {"a": 100.0, "b": 100.0}
    reporter._passed = 2
    reporter._failed = 1
    # queued = total - (passed + failed) - running = 6 - 3 - 2 = 1
    assert reporter._render(105.0, width=0)[0] == (
        "nox > --parallel: running 2 · passed 2 · failed 1 · queued 1"
    )
    # No running sessions -> nothing is drawn.
    reporter._active = {}
    assert reporter._render(105.0, width=0) == []
    # Narrow width hard-truncates the (plain) header.
    reporter._active = {"a": 100.0}
    header = reporter._render(105.0, width=8)[0]
    assert len(header) == 7
    assert "\x1b" not in header


def test_reporter_render_truncates_to_width() -> None:
    reporter = _parallel._Reporter(color=False, tty=False, total=1)
    reporter._active = {"a": 100.0}
    reporter._preview = {"a": "x" * 200}
    # Wide enough for the header plus a trimmed preview: fills width - 1.
    assert len(reporter._render(105.0, width=20)[1]) == 19
    # No room for a preview after the header: session line only, no trailing spaces.
    assert reporter._render(105.0, width=11)[1] == "⠋ a (5s)"
    # Too narrow even for the header: hard truncation to width - 1.
    line = reporter._render(105.0, width=5)[1]
    assert len(line) == 4
    assert "\x1b" not in line


def test_reporter_render_color() -> None:
    reporter = _parallel._Reporter(color=True, tty=False, total=1)
    reporter._active = {"a": 100.0}
    reporter._preview = {"a": "installing"}
    header, line = reporter._render(105.0, width=0)
    assert "\x1b[1m\x1b[35mnox > --parallel:\x1b[0m" in header  # bold purple prefix
    assert "\x1b[34m" in header  # blue "running"
    assert "\x1b[32m" in header  # green "passed"
    assert "\x1b[31m" in header  # red "failed"
    assert "\x1b[33m" in header  # yellow "queued"
    assert "\x1b[36m" in line  # cyan spinner/name
    assert "\x1b[32m" in line  # green elapsed time
    assert "\x1b[90minstalling\x1b[0m" in line  # grey preview
    assert "\x1b[1m" in line  # bold name


def test_reporter_update_preview() -> None:
    reporter = _parallel._Reporter(color=False, tty=False)
    reporter._active = {"a": 0.0}
    # ANSI escapes are stripped so truncation can't corrupt the terminal.
    reporter.update("a", "\x1b[32mnox > installing\x1b[0m\n")
    assert reporter._preview["a"] == "nox > installing"
    # Blank lines don't clobber the last meaningful preview.
    reporter.update("a", "   \n")
    assert reporter._preview["a"] == "nox > installing"
    # Carriage-return redraws keep only the latest segment.
    reporter.update("a", "10%\r50%\r100%\n")
    assert reporter._preview["a"] == "100%"


def test_reporter_started_and_finished(capsys: pytest.CaptureFixture[str]) -> None:
    with _parallel._Reporter(color=False, tty=False) as reporter:
        reporter.started("a")
        reporter.finished(
            "a",
            Result(_fake_runner(FakeSession("a")), Status.SUCCESS, duration=0.0),
            "session output\n",
        )
    out = capsys.readouterr().out
    assert "Starting session a..." in out
    assert "✓ a: success" in out
    assert "session output" in out


def test_reporter_aborted_shows_reason(capsys: pytest.CaptureFixture[str]) -> None:
    reporter = _parallel._Reporter(color=False, tty=False)
    reporter.finished(
        "e",
        Result(
            _fake_runner(FakeSession("e")),
            Status.ABORTED,
            reason="Prerequisite session d was not successful",
            duration=0,
        ),
        "",
    )
    out = capsys.readouterr().out
    assert "↯ e: aborted" in out
    assert "Prerequisite session d was not successful" in out
    assert reporter._failed == 1


def test_reporter_counts_skipped_separately() -> None:
    reporter = _parallel._Reporter(color=False, tty=False, total=3)
    reporter.finished(
        "s",
        Result(_fake_runner(FakeSession("s")), Status.SKIPPED, duration=0.0),
        "",
    )
    assert reporter._passed == 0
    assert reporter._skipped == 1
    reporter._active = {"a": 100.0}
    header = reporter._render(105.0, width=0)[0]
    assert "skipped 1" in header
    # queued = total - done - running = 3 - 1 - 1 = 1
    assert "queued 1" in header


def test_reporter_block_without_output_or_reason(
    capsys: pytest.CaptureFixture[str],
) -> None:
    reporter = _parallel._Reporter(color=False, tty=False)
    reporter._emit_block(
        "x",
        Result(_fake_runner(FakeSession("x")), Status.SUCCESS, duration=0),
        "",
    )
    out = capsys.readouterr().out
    assert "✓ x: success" in out


def test_run_session_spawns_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_child_argv(
        _global_config: object, _session: object, report_path: str
    ) -> list[str]:
        report = {
            "result": 1,
            "sessions": [
                {
                    "name": "x",
                    "result": "success",
                    "result_code": 1,
                    "reason": None,
                    "signatures": ["x"],
                    "duration": 0.5,
                }
            ],
        }
        code = (
            "import json,sys;"
            f"open({report_path!r}, 'w').write({json.dumps(json.dumps(report))});"
            "print('child output')"
        )
        return [sys.executable, "-c", code]

    monkeypatch.setattr(_parallel, "_child_argv", fake_child_argv)
    seen: list[str] = []
    result, output = _parallel._run_session(
        _fake_runner(FakeSession("x")),
        _config(),
        set(),
        threading.Lock(),
        on_line=seen.append,
    )
    assert result.status is Status.SUCCESS
    assert result.duration == 0.5
    assert "child output" in output
    assert any("child output" in line for line in seen)

    # Without a callback (the default), output is still captured.
    _, output2 = _parallel._run_session(
        _fake_runner(FakeSession("x")), _config(), set(), threading.Lock()
    )
    assert "child output" in output2


def test_run_session_preserves_carriage_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Progress-bar style \r redraws must reach the buffered block untranslated
    # so the terminal renders them as overwrites, not as separate lines.
    def fake_child_argv(
        _global_config: object, _session: object, _report_path: str
    ) -> list[str]:
        code = (
            "import sys;"
            " sys.stdout.write('10%\\r50%\\r100%\\n');"
            " sys.stdout.flush();"
            " sys.stdout.buffer.write(b'crlf\\r\\n')"
        )
        return [sys.executable, "-c", code]

    monkeypatch.setattr(_parallel, "_child_argv", fake_child_argv)
    seen: list[str] = []
    _, output = _parallel._run_session(
        _fake_runner(FakeSession("x")),
        _config(),
        set(),
        threading.Lock(),
        on_line=seen.append,
    )
    assert "10%\r50%\r100%\n" in output
    # Windows-style line endings are normalized so re-emitting the block
    # doesn't double the carriage returns.
    assert output.endswith("crlf\n")
    # The reader hands each \r-terminated segment to the preview callback.
    assert any(line.endswith("100%\n") for line in seen)


def test_stop_procs_escalates_to_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name != "posix":  # pragma: no cover
        pytest.skip("process groups are POSIX-only")
    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: signals.append((pgid, sig)))

    polite = mock.Mock(pid=101)
    polite.wait.return_value = 0
    stubborn = mock.Mock(pid=102)
    stubborn.wait.side_effect = [subprocess.TimeoutExpired("nox", 1), 0]

    _parallel._stop_procs([polite, stubborn])

    assert (101, signal.SIGTERM) in signals
    assert (102, signal.SIGTERM) in signals
    # Only the process that ignored SIGTERM gets SIGKILL.
    assert (102, signal.SIGKILL) in signals
    assert (101, signal.SIGKILL) not in signals


@pytest.mark.parametrize(
    ("value", "expected"),
    [("4", 4), (3, 3), (" auto ", None)],
)
def test_parse_parallel_valid(value: object, expected: int | None) -> None:
    result = _options.parse_parallel(typing.cast("typing.Any", value))
    if expected is None:
        assert result >= 1  # "auto" -> CPU count
    else:
        assert result == expected


@pytest.mark.parametrize("value", ["0", "-2", "bad", None])
def test_parse_parallel_invalid(value: object) -> None:
    with pytest.raises(ValueError, match="parallel"):
        _options.parse_parallel(typing.cast("typing.Any", value))


def test_parallel_cli_option() -> None:
    parser = _options.options.parser()
    assert isinstance(parser.parse_args(["-j", "auto"]).parallel, int)
    assert parser.parse_args(["--parallel", "5"]).parallel == 5
    with pytest.raises(SystemExit):
        parser.parse_args(["-j", "nope"])


def test_parallel_env_invalid_does_not_break_unrelated_commands(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # A stale/bad NOX_PARALLEL must not make every invocation (nox -l,
    # nox --version, ...) fail at argument parsing; warn and ignore it.
    monkeypatch.setenv("NOX_PARALLEL", "bogus")
    args = _options.options.parser().parse_args([])
    assert args.parallel is None
    assert any("NOX_PARALLEL" in record.message for record in caplog.records)


def test_parallel_env_valid_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOX_PARALLEL", "3")
    assert _options.options.parser().parse_args([]).parallel == 3


def test_run_manifest_invalid_noxfile_parallel_errors() -> None:
    # nox.options.parallel bypasses argparse; a bad value must produce a clean
    # error (exit code 3), not an uncaught ValueError traceback.
    config = _options.options.namespace(parallel="bogus", stop_on_first_error=False)
    manifest = types.SimpleNamespace(list_all_sessions=list)
    assert tasks.run_manifest(typing.cast("typing.Any", manifest), config) == 3


def test_run_manifest_zero_noxfile_parallel_errors() -> None:
    # 0 is invalid like on the command line, not a silent "sequential".
    config = _options.options.namespace(parallel=0, stop_on_first_error=False)
    manifest = types.SimpleNamespace(list_all_sessions=list)
    assert tasks.run_manifest(typing.cast("typing.Any", manifest), config) == 3


def test_notify_refused_in_no_dependencies_mode() -> None:
    # Under --parallel each child runs with --no-dependencies; notify() there
    # would run the target session concurrently with (and in addition to) its
    # own scheduled run, racing on the same envdir.
    runner = types.SimpleNamespace(
        global_config=types.SimpleNamespace(no_dependencies=True),
        manifest=mock.Mock(),
    )
    session = Session(typing.cast("SessionRunner", runner))
    with pytest.raises(ValueError, match="notify"):
        session.notify("other")
    runner.manifest.notify.assert_not_called()


def test_worker_skips_preview_callback_without_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Without a TTY no status board is drawn, so the per-line preview callback
    # is pure overhead and must not be wired up.
    captured: dict[str, object] = {"on_line": "unset"}

    def fake_run_session(
        session: SessionRunner,
        _global_config: object,
        _procs: object,
        _procs_lock: object,
        on_line: object = None,
    ) -> tuple[Result, str]:
        captured["on_line"] = on_line
        return Result(session, Status.SUCCESS, duration=0.0), ""

    monkeypatch.setattr(_parallel, "_run_session", fake_run_session)
    _run([FakeSession("a")], _config())
    assert captured["on_line"] is None


def test_parallel_noxfile_settable() -> None:
    assert hasattr(_options.options.noxfile_namespace(), "parallel")


def test_result_serialize_includes_reason() -> None:
    session = typing.cast(
        "SessionRunner",
        types.SimpleNamespace(func=types.SimpleNamespace(), name="x", signatures=["x"]),
    )
    result = Result(session, Status.SKIPPED, reason="why")
    assert result.serialize()["reason"] == "why"


def test_run_manifest_dispatches_to_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_parallel(
        _manifest: object, _global_config: object, jobs: int
    ) -> list[Result]:
        captured["jobs"] = jobs
        return []

    monkeypatch.setattr(_parallel, "run_manifest_parallel", fake_parallel)
    config = _options.options.namespace(parallel=3, stop_on_first_error=False)
    manifest = types.SimpleNamespace(
        list_all_sessions=lambda: [(FakeSession("a"), True)]
    )
    tasks.run_manifest(typing.cast("typing.Any", manifest), config)
    assert captured["jobs"] == 3
