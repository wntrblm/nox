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

import argparse
import builtins
import copy
import json
import os
import platform
import typing
from pathlib import Path
from textwrap import dedent
from unittest import mock

import pytest

import nox
import nox._decorators
from nox import _options, sessions, tasks
from nox.manifest import WARN_PYTHONS_IGNORED, Manifest

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from types import ModuleType

RESOURCES = os.path.join(os.path.dirname(__file__), "resources")


def session_func_raw() -> None:
    pass


session_func = typing.cast("nox._decorators.Func", session_func_raw)


session_func.python = None
session_func.venv_backend = None
session_func.should_warn = {}
session_func.tags = []
session_func.default = True
session_func.requires = []


def session_func_with_python_raw() -> None:
    pass


session_func_with_python = typing.cast(
    "nox._decorators.Func", session_func_with_python_raw
)


session_func_with_python.python = "3.8"
session_func_with_python.venv_backend = None
session_func_with_python.default = True
session_func_with_python.requires = []


def session_func_venv_pythons_warning_raw() -> None:
    pass


session_func_venv_pythons_warning = typing.cast(
    "nox._decorators.Func", session_func_venv_pythons_warning_raw
)


session_func_venv_pythons_warning.python = ["3.7"]
session_func_venv_pythons_warning.venv_backend = "none"
session_func_venv_pythons_warning.should_warn = {WARN_PYTHONS_IGNORED: ["3.7"]}


def test_load_nox_module() -> None:
    config = _options.options.namespace(noxfile=os.path.join(RESOURCES, "noxfile.py"))
    noxfile_module = tasks.load_nox_module(config)
    assert not isinstance(noxfile_module, int)
    assert noxfile_module.SIGIL == "123"


def test_load_nox_module_expandvars() -> None:
    # Assert that variables are expanded when looking up the path to the Noxfile
    # This is particular importand in Windows when one needs to use variables like
    # %TEMP% to point to the noxfile.py
    with mock.patch.dict(os.environ, {"RESOURCES_PATH": RESOURCES}):
        if platform.system().lower().startswith("win"):
            config = _options.options.namespace(noxfile="%RESOURCES_PATH%/noxfile.py")
        else:
            config = _options.options.namespace(noxfile="${RESOURCES_PATH}/noxfile.py")
        noxfile_module = tasks.load_nox_module(config)
    assert not isinstance(noxfile_module, int)
    assert noxfile_module.__file__ == os.path.join(RESOURCES, "noxfile.py")
    assert noxfile_module.SIGIL == "123"


def test_load_nox_module_not_found(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    bogus_noxfile = tmp_path / "bogus.py"
    config = _options.options.namespace(noxfile=str(bogus_noxfile))

    assert tasks.load_nox_module(config) == 2
    assert (
        f"Failed to load Noxfile {bogus_noxfile}, no such file exists." in caplog.text
    )


def test_load_nox_module_os_error(caplog: pytest.LogCaptureFixture) -> None:
    noxfile = os.path.join(RESOURCES, "noxfile.py")
    config = _options.options.namespace(noxfile=noxfile)
    with mock.patch("nox.tasks.check_nox_version", autospec=True) as version_checker:
        version_checker.side_effect = OSError
        assert tasks.load_nox_module(config) == 2
        assert f"Failed to load Noxfile {noxfile}" in caplog.text


@pytest.fixture(autouse=True)
def reset_needs_version() -> Generator[None, None, None]:
    """Do not leak ``nox.needs_version`` between tests."""
    try:
        yield
    finally:
        nox.needs_version = None


@pytest.fixture
def reset_global_nox_options() -> None:
    nox.options = _options.options.noxfile_namespace()


def test_load_nox_module_needs_version_static(tmp_path: Path) -> None:
    text = dedent(
        """
        import nox
        nox.needs_version = ">=9999.99.99"
        """
    )
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text(text, encoding="utf-8")
    config = _options.options.namespace(noxfile=str(noxfile))
    assert tasks.load_nox_module(config) == 2


def test_load_nox_module_needs_version_dynamic(tmp_path: Path) -> None:
    text = dedent(
        """
        import nox
        NOX_NEEDS_VERSION = ">=9999.99.99"
        nox.needs_version = NOX_NEEDS_VERSION
        """
    )
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text(text, encoding="utf-8")
    config = _options.options.namespace(noxfile=str(noxfile))
    tasks.load_nox_module(config)
    # Dynamic version requirements are not checked.
    assert nox.needs_version == ">=9999.99.99"


def test_discover_session_functions_decorator() -> None:
    # Define sessions using the decorator.
    @nox.session
    def foo() -> None:
        pass

    @nox.session
    def bar() -> None:
        pass

    @nox.session(name="not-a-bar")
    def not_a_bar() -> None:
        pass

    def notasession() -> None:
        pass

    # Mock up a noxfile.py module and configuration.
    mock_module = typing.cast(
        "ModuleType",
        argparse.Namespace(
            __name__=foo.__module__, foo=foo, bar=bar, notasession=notasession
        ),
    )
    config = _options.options.namespace(sessions=(), keywords=(), posargs=[])

    # Get the manifest and establish that it looks like what we expect.
    manifest = tasks.discover_manifest(mock_module, config)
    sessions = list(manifest)
    assert [s.func for s in sessions] == [foo, bar, not_a_bar]
    assert [i.friendly_name for i in sessions] == ["foo", "bar", "not-a-bar"]


def test_filter_manifest() -> None:
    config = _options.options.namespace(
        sessions=None, pythons=(), keywords=(), posargs=[]
    )
    manifest = Manifest({"foo": session_func, "bar": session_func}, config)
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value is manifest
    assert len(manifest) == 2


def test_filter_manifest_not_found() -> None:
    config = _options.options.namespace(
        sessions=("baz",), pythons=(), keywords=(), posargs=[]
    )
    manifest = Manifest({"foo": session_func, "bar": session_func}, config)
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value == 3


def test_filter_manifest_pythons() -> None:
    config = _options.options.namespace(
        sessions=None, pythons=("3.8",), keywords=(), posargs=[]
    )
    manifest = Manifest(
        {"foo": session_func_with_python, "bar": session_func, "baz": session_func},
        config,
    )
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value is manifest
    assert len(manifest) == 1


def test_filter_manifest_pythons_not_found(caplog: pytest.LogCaptureFixture) -> None:
    config = _options.options.namespace(
        sessions=None, pythons=("1.2",), keywords=(), posargs=[]
    )
    manifest = Manifest(
        {"foo": session_func_with_python, "bar": session_func, "baz": session_func},
        config,
    )
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value == 3
    assert "Python version selection caused no sessions to be selected." in caplog.text


def test_filter_manifest_keywords() -> None:
    config = _options.options.namespace(
        sessions=None, pythons=(), keywords="foo or bar", posargs=[]
    )
    manifest = Manifest(
        {"foo": session_func, "bar": session_func, "baz": session_func}, config
    )
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value is manifest
    assert len(manifest) == 2


def test_filter_manifest_keywords_not_found(caplog: pytest.LogCaptureFixture) -> None:
    config = _options.options.namespace(
        sessions=None, pythons=(), keywords="mouse or python", posargs=[]
    )
    manifest = Manifest(
        {"foo": session_func, "bar": session_func, "baz": session_func}, config
    )
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value == 3
    assert "No sessions selected after filtering by keyword." in caplog.text


def test_filter_manifest_keywords_syntax_error() -> None:
    config = _options.options.namespace(
        sessions=None, pythons=(), keywords="foo:bar", posargs=[]
    )
    manifest = Manifest({"foo_bar": session_func, "foo_baz": session_func}, config)
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value == 3


@pytest.mark.parametrize(
    ("tags", "session_count"),
    [
        (None, 8),
        (["foo"], 7),
        (["bar"], 5),
        (["baz"], 3),
        (["foo", "bar"], 8),
        (["foo", "baz"], 7),
        (["bar", "baz"], 6),
        (["foo", "bar", "baz"], 8),
    ],
)
def test_filter_manifest_tags(
    tags: None | builtins.list[builtins.str],
    session_count: builtins.int,
) -> None:
    @nox.session(tags=["foo"])
    def qux() -> None:
        pass

    @nox.session(tags=["bar"])
    def quux() -> None:
        pass

    @nox.session(tags=["foo", "bar"])
    def quuz() -> None:
        pass

    @nox.session(tags=["foo", "bar", "baz"])
    def corge() -> None:
        pass

    @nox.session(tags=["foo"])
    @nox.parametrize("a", [1, nox.param(2, tags=["bar"])])
    @nox.parametrize("b", [3, 4], tags=[["baz"]])
    def grault() -> None:
        pass

    config = _options.options.namespace(
        sessions=None, pythons=(), posargs=[], tags=tags
    )
    manifest = Manifest(
        {
            "qux": qux,
            "quux": quux,
            "quuz": quuz,
            "corge": corge,
            "grault": grault,
        },
        config,
    )
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value is manifest
    assert len(manifest) == session_count


@pytest.mark.parametrize(
    "tags",
    [
        ["Foo"],
        ["not-found"],
    ],
    ids=[
        "tags-are-case-insensitive",
        "tag-does-not-exist",
    ],
)
def test_filter_manifest_tags_not_found(
    tags: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    @nox.session(tags=["foo"])
    def quux() -> None:
        pass

    config = _options.options.namespace(
        sessions=None, pythons=(), posargs=[], tags=tags
    )
    manifest = Manifest({"quux": quux}, config)
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value == 3
    assert "Tag selection caused no sessions to be selected." in caplog.text


@pytest.mark.usefixtures("reset_global_nox_options")
def test_merge_tags(generate_noxfile_options: Callable[..., str]) -> None:
    @nox.session(tags=["foobar"])
    def testing() -> None:
        pass

    @nox.session(tags=["foobar"])
    def bar() -> None:
        pass

    noxfile_path = generate_noxfile_options(reuse_existing_virtualenvs=True)
    config = _options.options.namespace(
        noxfile=noxfile_path,
        sessions=None,
        pythons=(),
        posargs=[],
        tags=["foobar"],
    )

    nox_module = tasks.load_nox_module(config)
    assert not isinstance(nox_module, int)
    tasks.merge_noxfile_options(nox_module, config)
    manifest = Manifest({"testing": testing, "bar": bar}, config)
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value is manifest
    assert len(manifest) == 2


@pytest.mark.parametrize("selection", [None, ["qux"], ["quuz"], ["qux", "quuz"]])
def test_default_false(selection: None | builtins.list[builtins.str]) -> None:
    @nox.session()
    def qux() -> None:
        pass

    @nox.session()
    def quux() -> None:
        pass

    @nox.session(default=False)
    def quuz() -> None:
        pass

    @nox.session(default=False)
    def corge() -> None:
        pass

    config = _options.options.namespace(sessions=selection, pythons=(), posargs=[])
    manifest = Manifest(
        {
            "qux": qux,
            "quux": quux,
            "quuz": quuz,
            "corge": corge,
        },
        config,
    )
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value is manifest
    expected = 2 if selection is None else len(selection)
    assert len(manifest) == expected


def test_honor_list_request_noop() -> None:
    config = _options.options.namespace(list_sessions=False)
    manifest = typing.cast("Manifest", {"thing": mock.sentinel.THING})
    return_value = tasks.honor_list_request(manifest, global_config=config)
    assert return_value is manifest


@pytest.mark.parametrize(
    ("description", "module_docstring"),
    [
        (None, None),
        (None, "hello docstring"),
        ("Bar", None),
        ("Bar", "hello docstring"),
    ],
)
def test_honor_list_request(
    description: None | builtins.str, module_docstring: None | builtins.str
) -> None:
    config = _options.options.namespace(
        list_sessions=True, noxfile="noxfile.py", color=False
    )
    manifest = mock.create_autospec(Manifest)
    manifest.module_docstring = module_docstring
    manifest.list_all_sessions.return_value = [
        (
            argparse.Namespace(friendly_name="foo", description=description, tags=[]),
            True,
        )
    ]
    return_value = tasks.honor_list_request(manifest, global_config=config)
    assert return_value == 0


def test_honor_list_request_skip_and_selected(
    capsys: pytest.CaptureFixture[builtins.str],
) -> None:
    config = _options.options.namespace(
        list_sessions=True, noxfile="noxfile.py", color=False
    )
    manifest = mock.create_autospec(Manifest)
    manifest.module_docstring = None
    manifest.list_all_sessions.return_value = [
        (argparse.Namespace(friendly_name="foo", description=None, tags=[]), True),
        (argparse.Namespace(friendly_name="bar", description=None, tags=[]), False),
    ]
    return_value = tasks.honor_list_request(manifest, global_config=config)
    assert return_value == 0

    out = capsys.readouterr().out

    assert "* foo" in out
    assert "- bar" in out


def test_honor_list_request_prints_docstring_if_present(
    capsys: pytest.CaptureFixture[builtins.str],
) -> None:
    config = _options.options.namespace(
        list_sessions=True, noxfile="noxfile.py", color=False
    )
    manifest = mock.create_autospec(Manifest)
    manifest.module_docstring = "Hello I'm a docstring"
    manifest.list_all_sessions.return_value = [
        (argparse.Namespace(friendly_name="foo", description=None, tags=[]), True),
        (argparse.Namespace(friendly_name="bar", description=None, tags=[]), False),
    ]

    return_value = tasks.honor_list_request(manifest, global_config=config)
    assert return_value == 0

    out = capsys.readouterr().out

    assert "Hello I'm a docstring" in out


def test_honor_list_request_doesnt_print_docstring_if_not_present(
    capsys: pytest.CaptureFixture[builtins.str],
) -> None:
    config = _options.options.namespace(
        list_sessions=True, noxfile="noxfile.py", color=False
    )
    manifest = mock.create_autospec(Manifest)
    manifest.module_docstring = None
    manifest.list_all_sessions.return_value = [
        (argparse.Namespace(friendly_name="foo", description=None, tags=[]), True),
        (argparse.Namespace(friendly_name="bar", description=None, tags=[]), False),
    ]

    return_value = tasks.honor_list_request(manifest, global_config=config)
    assert return_value == 0

    out = capsys.readouterr().out

    assert "Hello I'm a docstring" not in out


def test_honor_list_json_request(capsys: pytest.CaptureFixture[builtins.str]) -> None:
    config = _options.options.namespace(
        list_sessions=True, noxfile="noxfile.py", json=True
    )
    manifest = mock.create_autospec(Manifest)
    manifest.list_all_sessions.return_value = [
        (
            argparse.Namespace(
                name="bar",
                friendly_name="foo",
                description="simple",
                func=argparse.Namespace(python=Path("123")),
                tags=[],
            ),
            True,
        ),
        (
            argparse.Namespace(),
            False,
        ),
    ]
    return_value = tasks.honor_list_request(manifest, global_config=config)
    assert return_value == 0
    assert json.loads(capsys.readouterr().out) == [
        {
            "session": "foo",
            "name": "bar",
            "description": "simple",
            "python": "123",
            "tags": [],
            "call_spec": {},
        }
    ]


def test_refuse_json_nolist_request(caplog: pytest.LogCaptureFixture) -> None:
    config = _options.options.namespace(
        list_sessions=False, noxfile="noxfile.py", json=True
    )
    manifest = mock.create_autospec(Manifest)
    manifest.list_all_sessions.return_value = [
        (
            argparse.Namespace(
                name="bar",
                friendly_name="foo",
                description="simple",
                func=argparse.Namespace(python="123"),
                tags=[],
            ),
            True,
        )
    ]
    return_value = tasks.honor_list_request(manifest, global_config=config)
    assert return_value == 3
    (record,) = caplog.records
    assert record.message == "Must specify --list-sessions with --json"


def test_empty_session_list_in_noxfile(
    capsys: pytest.CaptureFixture[builtins.str],
) -> None:
    config = _options.options.namespace(noxfile="noxfile.py", sessions=(), posargs=[])
    manifest = Manifest({"session": session_func}, config)
    return_value = tasks.filter_manifest(manifest, global_config=config)
    assert return_value == 0
    assert "No sessions selected." in capsys.readouterr().out


def test_empty_session_None_in_noxfile() -> None:
    config = _options.options.namespace(noxfile="noxfile.py", sessions=None, posargs=[])
    manifest = Manifest({"session": session_func}, config)
    return_value = tasks.filter_manifest(manifest, global_config=config)
    assert return_value == manifest


def test_verify_manifest_empty() -> None:
    config = _options.options.namespace(sessions=(), keywords=())
    manifest = Manifest({}, config)
    return_value = tasks.filter_manifest(manifest, global_config=config)
    assert return_value == 3


def test_verify_manifest_nonempty() -> None:
    config = _options.options.namespace(sessions=None, keywords=(), posargs=[])
    manifest = Manifest({"session": session_func}, config)
    return_value = tasks.filter_manifest(manifest, global_config=config)
    assert return_value == manifest


def test_verify_manifest_list(capsys: pytest.CaptureFixture[builtins.str]) -> None:
    config = _options.options.namespace(sessions=(), keywords=(), posargs=[])
    manifest = Manifest({"session": session_func}, config)
    return_value = tasks.filter_manifest(manifest, global_config=config)
    assert return_value == 0
    assert "Please select a session" in capsys.readouterr().out


@pytest.mark.parametrize("with_warnings", [False, True], ids="with_warnings={}".format)
def test_run_manifest(with_warnings: builtins.bool) -> None:
    # Set up a valid manifest.
    config = _options.options.namespace(stop_on_first_error=False)
    sessions_ = [
        typing.cast("sessions.SessionRunner", mock.Mock(spec=sessions.SessionRunner)),
        typing.cast("sessions.SessionRunner", mock.Mock(spec=sessions.SessionRunner)),
    ]
    manifest = Manifest({}, config)
    manifest._queue = copy.copy(sessions_)

    # Ensure each of the mocks returns a successful result
    for mock_session in sessions_:
        mock_session.execute.return_value = sessions.Result(  # type: ignore[attr-defined]
            session=mock_session, status=sessions.Status.SUCCESS
        )
        # we need the should_warn attribute, add some func
        if with_warnings:
            mock_session.name = "hello"
            mock_session.func = session_func_venv_pythons_warning
        else:
            mock_session.func = session_func

    # Run the manifest.
    results = tasks.run_manifest(manifest, global_config=config)

    # Verify the results look correct.
    assert len(results) == 2
    assert results[0].session == sessions_[0]
    assert results[1].session == sessions_[1]
    for result in results:
        assert isinstance(result, sessions.Result)
        assert result.status == sessions.Status.SUCCESS


def test_run_manifest_abort_on_first_failure() -> None:
    # Set up a valid manifest.
    config = _options.options.namespace(stop_on_first_error=True)
    sessions_ = [
        typing.cast("sessions.SessionRunner", mock.Mock(spec=sessions.SessionRunner)),
        typing.cast("sessions.SessionRunner", mock.Mock(spec=sessions.SessionRunner)),
    ]
    manifest = Manifest({}, config)
    manifest._queue = copy.copy(sessions_)

    # Ensure each of the mocks returns a successful result.
    for mock_session in sessions_:
        mock_session.execute.return_value = sessions.Result(  # type: ignore[attr-defined]
            session=mock_session, status=sessions.Status.FAILED
        )
        # we need the should_warn attribute, add some func
        mock_session.func = session_func

    # Run the manifest.
    results = tasks.run_manifest(manifest, global_config=config)

    # Verify the results look correct.
    assert len(results) == 1
    assert isinstance(results[0], sessions.Result)
    assert results[0].session == sessions_[0]
    assert results[0].status == sessions.Status.FAILED

    # Verify that only the first session was called.
    assert sessions_[0].execute.called  # type: ignore[attr-defined]
    assert not sessions_[1].execute.called  # type: ignore[attr-defined]


def test_print_summary_one_result() -> None:
    results = [mock.sentinel.RESULT]
    with mock.patch("nox.tasks.logger", autospec=True) as logger:
        answer = tasks.print_summary(results, argparse.Namespace())
        assert not logger.warning.called
        assert not logger.success.called
        assert not logger.error.called
    assert answer is results


def test_print_summary() -> None:
    with mock.patch.object(sessions.Result, "log") as mock_log:
        results = [
            sessions.Result(
                session=typing.cast(
                    "sessions.SessionRunner",
                    argparse.Namespace(friendly_name="foo"),
                ),
                status=sessions.Status.SUCCESS,
            ),
            sessions.Result(
                session=typing.cast(
                    "sessions.SessionRunner",
                    argparse.Namespace(friendly_name="bar"),
                ),
                status=sessions.Status.FAILED,
            ),
            sessions.Result(
                session=typing.cast(
                    "sessions.SessionRunner",
                    argparse.Namespace(friendly_name="baz"),
                ),
                status=sessions.Status.SKIPPED,
            ),
            sessions.Result(
                session=typing.cast(
                    "sessions.SessionRunner",
                    argparse.Namespace(friendly_name="qux"),
                ),
                status=sessions.Status.SKIPPED,
                reason="something reason",
            ),
        ]

        answer = tasks.print_summary(results, argparse.Namespace())

        assert mock_log.call_count == 4
        calls = mock_log.call_args_list
        assert calls[0][0][0] == "* foo: success"
        assert calls[1][0][0] == "* bar: failed"
        assert calls[2][0][0] == "* baz: skipped"
        assert calls[3][0][0] == "* qux: skipped (something reason)"

    assert answer is results


def test_create_report_noop() -> None:
    config = _options.options.namespace(report=None)
    with mock.patch.object(builtins, "open", autospec=True) as open_:
        results = tasks.create_report(mock.sentinel.RESULTS, config)
        assert not open_.called
    assert results is mock.sentinel.RESULTS


def test_create_report() -> None:
    config = _options.options.namespace(report="/path/to/report")
    results = [
        sessions.Result(
            session=typing.cast(
                "sessions.SessionRunner",
                argparse.Namespace(signatures=["foosig"], name="foo", func=object()),
            ),
            status=sessions.Status.SUCCESS,
        )
    ]
    with mock.patch.object(builtins, "open", autospec=True) as open_:
        with mock.patch.object(json, "dump", autospec=True) as dump:
            answer = tasks.create_report(results, config)
            assert answer is results
            dump.assert_called_once_with(
                {
                    "result": 1,
                    "sessions": [
                        {
                            "name": "foo",
                            "signatures": ["foosig"],
                            "result": "success",
                            "result_code": 1,
                            "args": {},
                            "duration": 0.0,
                        }
                    ],
                },
                mock.ANY,
                indent=2,
            )
        open_.assert_called_once_with("/path/to/report", "w", encoding="utf-8")


def test_honor_usage_request_noop() -> None:
    config = _options.options.namespace(usage=None)
    manifest = typing.cast("Manifest", {"thing": mock.sentinel.THING})
    return_value = tasks.honor_usage_request(manifest, global_config=config)
    assert return_value is manifest


def test_honor_usage_request_with_docstring(
    capsys: pytest.CaptureFixture[builtins.str],
) -> None:
    config = _options.options.namespace(usage=["my_session"])
    manifest = mock.create_autospec(Manifest)
    session = argparse.Namespace(
        name="my_session",
        signatures=["my_session"],
        full_description="Full docstring\n\nWith details",
    )
    manifest._all_sessions = [session]
    return_value = tasks.honor_usage_request(manifest, global_config=config)
    assert return_value == 0
    out = capsys.readouterr().out
    assert "Full docstring\n\nWith details" in out


def test_honor_usage_request_no_docstring() -> None:
    config = _options.options.namespace(usage=["my_session"])
    manifest = mock.create_autospec(Manifest)
    session = argparse.Namespace(
        name="my_session",
        signatures=["my_session"],
        full_description=None,
    )
    manifest._all_sessions = [session]
    return_value = tasks.honor_usage_request(manifest, global_config=config)
    assert return_value == 1


def test_honor_usage_request_skips_non_matching_sessions(
    capsys: pytest.CaptureFixture[builtins.str],
) -> None:
    config = _options.options.namespace(usage=["second"])
    manifest = mock.create_autospec(Manifest)
    first = argparse.Namespace(
        name="first",
        signatures=["first"],
        full_description="First docstring",
    )
    second = argparse.Namespace(
        name="second",
        signatures=["second"],
        full_description="Second docstring",
    )
    manifest._all_sessions = [first, second]
    return_value = tasks.honor_usage_request(manifest, global_config=config)
    assert return_value == 0
    out = capsys.readouterr().out
    assert "Second docstring" in out


def test_honor_usage_request_session_not_found() -> None:
    config = _options.options.namespace(usage=["nonexistent"])
    manifest = mock.create_autospec(Manifest)
    manifest._all_sessions = []
    return_value = tasks.honor_usage_request(manifest, global_config=config)
    assert return_value == 1


def test_final_reduce() -> None:
    config = argparse.Namespace()
    true = typing.cast("sessions.Result", True)  # noqa: FBT003
    false = typing.cast("sessions.Result", False)  # noqa: FBT003
    assert tasks.final_reduce([true, true], config) == 0
    assert tasks.final_reduce([true, false], config) == 1
    assert tasks.final_reduce([], config) == 0
