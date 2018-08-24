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

from unittest import mock

from nox import workflow


def test_simple_workflow():
    # Set up functions for the workflow.
    function_a = mock.Mock(spec=())
    function_b = mock.Mock(spec=())
    function_c = mock.Mock(spec=())

    # Execute the workflow.
    exit_code = workflow.execute(
        workflow=(function_a, function_b, function_c),
        global_config=mock.sentinel.CONFIG,
    )

    # There were no errors; the final exit code should be 0.
    assert exit_code == 0

    # Each function should have been called with the previous one's
    # return value.
    function_a.assert_called_once_with(global_config=mock.sentinel.CONFIG)
    function_b.assert_called_once_with(
        function_a.return_value, global_config=mock.sentinel.CONFIG
    )
    function_c.assert_called_once_with(
        function_b.return_value, global_config=mock.sentinel.CONFIG
    )


def test_workflow_int_cutoff():
    # Set up functions for the workflow.
    function_a = mock.Mock(spec=())
    function_b = mock.Mock(spec=())
    function_c = mock.Mock(spec=())

    # This time, function_b will stop the process by returning an exit
    # code outright.
    function_b.return_value = 42

    # Execute the workflow.
    exit_code = workflow.execute(
        workflow=(function_a, function_b, function_c),
        global_config=mock.sentinel.CONFIG,
    )

    # There were no errors; the final exit code should be 0.
    assert exit_code == 42

    # Each function should have been called with the previous one's
    # return value.
    function_a.assert_called_once_with(global_config=mock.sentinel.CONFIG)
    function_b.assert_called_once_with(
        function_a.return_value, global_config=mock.sentinel.CONFIG
    )
    assert not function_c.called


def test_workflow_interrupted():
    # Set up functions for the workflow.
    function_a = mock.Mock(spec=())
    function_b = mock.Mock(spec=())
    function_c = mock.Mock(spec=())

    # This time, function_b will stop the process by returning an exit
    # code outright.
    function_b.side_effect = KeyboardInterrupt

    # Execute the workflow.
    exit_code = workflow.execute(
        workflow=(function_a, function_b, function_c),
        global_config=mock.sentinel.CONFIG,
    )

    # There were no errors; the final exit code should be 0.
    assert exit_code == 130

    # Each function should have been called with the previous one's
    # return value.
    function_a.assert_called_once_with(global_config=mock.sentinel.CONFIG)
    function_b.assert_called_once_with(
        function_a.return_value, global_config=mock.sentinel.CONFIG
    )
    assert not function_c.called
