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

import copy
import io
import json
import os
from unittest import mock

import nox
from nox import registry
from nox import sessions
from nox import tasks
from nox._testing import Namespace
from nox.manifest import Manifest


RESOURCES = os.path.join(os.path.dirname(__file__), 'resources')


def session_func():
    pass


session_func.python_config = registry.PythonConfig()


def test_load_nox_module():
    config = Namespace(noxfile=os.path.join(RESOURCES, 'noxfile.py'))
    noxfile_module = tasks.load_nox_module(config)
    assert noxfile_module.SIGIL == '123'


def test_load_nox_module_not_found():
    config = Namespace(noxfile='bogus.py')
    assert tasks.load_nox_module(config) == 2


def test_discover_session_functions_decorator():
    # Define sessions using the decorator.
    @nox.session
    def foo():
        pass

    @nox.session
    def bar():
        pass

    def notasession():
        pass

    # Mock up a nox.py module and configuration.
    mock_module = Namespace(
        __name__=foo.__module__,
        foo=foo,
        bar=bar,
        notasession=notasession,
    )
    config = Namespace(sessions=(), keywords=())

    # Get the manifest and establish that it looks like what we expect.
    manifest = tasks.discover_manifest(mock_module, config)
    sessions = list(manifest)
    assert [s.func for s in sessions] == [foo, bar]
    assert [str(i) for i in sessions] == ['foo', 'bar']


def test_filter_manifest():
    config = Namespace(sessions=(), keywords=())
    manifest = Manifest({
        'foo': session_func,
        'bar': session_func,
    }, config)
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value is manifest
    assert len(manifest) == 2


def test_filter_manifest_not_found():
    config = Namespace(sessions=('baz',), keywords=())
    manifest = Manifest({
        'foo': session_func,
        'bar': session_func,
    }, config)
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value == 3


def test_filter_manifest_keywords():
    config = Namespace(sessions=(), keywords='foo or bar')
    manifest = Manifest({
        'foo': session_func,
        'bar': session_func,
        'baz': session_func,
    }, config)
    return_value = tasks.filter_manifest(manifest, config)
    assert return_value is manifest
    assert len(manifest) == 2


def test_honor_list_request_noop():
    config = Namespace(list_sessions=False)
    manifest = {'thing': mock.sentinel.THING}
    return_value = tasks.honor_list_request(manifest, global_config=config)
    assert return_value is manifest


def test_honor_list_request():
    config = Namespace(list_sessions=True)
    manifest = [Namespace(signature='foo')]
    return_value = tasks.honor_list_request(manifest, global_config=config)
    assert return_value == 0


def test_verify_manifest_empty():
    config = Namespace(sessions=(), keywords=())
    manifest = Manifest({}, config)
    return_value = tasks.verify_manifest_nonempty(
        manifest,
        global_config=config,
    )
    assert return_value == 3


def test_verify_manifest_nonempty():
    config = Namespace(sessions=(), keywords=())
    manifest = Manifest({'session': session_func}, config)
    return_value = tasks.verify_manifest_nonempty(
        manifest,
        global_config=config,
    )
    assert return_value == manifest


def test_run_manifest():
    # Set up a valid manifest.
    config = Namespace(stop_on_first_error=False)
    sessions_ = [
        mock.Mock(spec=sessions.SessionRunner),
        mock.Mock(spec=sessions.SessionRunner),
    ]
    manifest = Manifest({}, config)
    manifest._queue = copy.copy(sessions_)

    # Ensure each of the mocks returns a successful result
    for mock_session in sessions_:
        mock_session.execute.return_value = sessions.Result(
            session=mock_session,
            status=sessions.Status.SUCCESS,
        )

    # Run the manifest.
    results = tasks.run_manifest(manifest, global_config=config)

    # Verify the results look correct.
    assert len(results) == 2
    assert results[0].session == sessions_[0]
    assert results[1].session == sessions_[1]
    for result in results:
        assert isinstance(result, sessions.Result)
        assert result.status == sessions.Status.SUCCESS


def test_run_manifest_abort_on_first_failure():
    # Set up a valid manifest.
    config = Namespace(stop_on_first_error=True)
    sessions_ = [
        mock.Mock(spec=sessions.SessionRunner),
        mock.Mock(spec=sessions.SessionRunner),
    ]
    manifest = Manifest({}, config)
    manifest._queue = copy.copy(sessions_)

    # Ensure each of the mocks returns a successful result.
    for mock_session in sessions_:
        mock_session.execute.return_value = sessions.Result(
            session=mock_session,
            status=sessions.Status.FAILED,
        )

    # Run the manifest.
    results = tasks.run_manifest(manifest, global_config=config)

    # Verify the results look correct.
    assert len(results) == 1
    assert isinstance(results[0], sessions.Result)
    assert results[0].session == sessions_[0]
    assert results[0].status == sessions.Status.FAILED

    # Verify that only the first session was called.
    assert sessions_[0].execute.called
    assert not sessions_[1].execute.called


def test_print_summary_one_result():
    results = [mock.sentinel.RESULT]
    with mock.patch('nox.tasks.logger', autospec=True) as logger:
        answer = tasks.print_summary(results, object())
        assert not logger.warning.called
        assert not logger.success.called
        assert not logger.error.called
    assert answer is results


def test_print_summary():
    results = [
        sessions.Result(session='foo', status=sessions.Status.SUCCESS),
        sessions.Result(session='bar', status=sessions.Status.FAILED),
    ]
    with mock.patch.object(sessions.Result, 'log', autospec=True) as log:
        answer = tasks.print_summary(results, object())
        assert log.call_count == 2
    assert answer is results


def test_create_report_noop():
    config = Namespace(report=None)
    with mock.patch.object(io, 'open', autospec=True) as open_:
        results = tasks.create_report(mock.sentinel.RESULTS, config)
        assert not open_.called
    assert results is mock.sentinel.RESULTS


def test_create_report():
    config = Namespace(report='/path/to/report')
    results = [sessions.Result(
        session=Namespace(signature='foosig', name='foo', func=object()),
        status=sessions.Status.SUCCESS,
    )]
    with mock.patch.object(io, 'open', autospec=True) as open_:
        with mock.patch.object(json, 'dump', autospec=True) as dump:
            answer = tasks.create_report(results, config)
            assert answer is results
            dump.assert_called_once_with({
                'result': 1,
                'sessions': [{
                    'name': 'foo',
                    'signature': 'foosig',
                    'result': 'success',
                    'result_code': 1,
                    'args': {},
                }],
            }, mock.ANY, indent=2)
        open_.assert_called_once_with('/path/to/report', 'w')


def test_final_reduce():
    config = object()
    assert tasks.final_reduce([True, True], config) == 0
    assert tasks.final_reduce([True, False], config) == 1
    assert tasks.final_reduce([], config) == 0
