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
import sys
import threading
import types
import typing

import pytest

from nox import _options, _parallel, tasks
from nox.manifest import Manifest
from nox.sessions import Result, SessionRunner, Status

if typing.TYPE_CHECKING:
    from collections.abc import Sequence


class FakeSession:
    """A minimal stand-in for ``SessionRunner`` for scheduler tests."""

    def __init__(self, name: str, deps: Sequence[FakeSession] = ()) -> None:
        self.friendly_name = name
        self.func = types.SimpleNamespace(should_warn={})
        self._deps = list(deps)

    def get_direct_dependencies(self) -> list[FakeSession]:
        return self._deps


def _fake_runner(session: FakeSession) -> SessionRunner:
    return typing.cast("SessionRunner", session)


def _config(**kwargs: object) -> object:
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
    assert argv[-3:] == ["--", "-k", "foo"]


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
        "running 2  passed 0  failed 0  queued 0",
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
        "running 2  passed 2  failed 1  queued 1"
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
    assert "\x1b[32m" in header  # green "passed"
    assert "\x1b[31m" in header  # red "failed"
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
    reporter.aborted(
        "e",
        Result(
            _fake_runner(FakeSession("e")),
            Status.ABORTED,
            reason="Prerequisite session d was not successful",
            duration=0,
        ),
    )
    out = capsys.readouterr().out
    assert "↯ e: aborted" in out
    assert "Prerequisite session d was not successful" in out


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


def test_parallel_noxfile_settable() -> None:
    assert hasattr(_options.options.noxfile_namespace(), "parallel")


def test_no_dependencies_skips_add_dependencies() -> None:
    config = _options.options.namespace(no_dependencies=True)
    manifest = Manifest({}, config)
    sentinel: list[object] = [object()]
    manifest._queue = typing.cast("typing.Any", sentinel)
    manifest.add_dependencies()
    # The queue is left untouched: no dependencies pulled in, no reordering.
    assert manifest._queue is sentinel


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
    tasks.run_manifest(typing.cast("typing.Any", []), config)
    assert captured["jobs"] == 3
