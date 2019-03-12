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

from nox import logger


def test_success():
    with mock.patch.object(logger.LoggerWithSuccessAndOutput, "_log") as _log:
        logger.LoggerWithSuccessAndOutput("foo").success("bar")
        _log.assert_called_once_with(logger.SUCCESS, "bar", ())
