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

import logging
from unittest import mock

import pytest
from nox import logger


def test_success():
    with mock.patch.object(logger.LoggerWithSuccessAndOutput, "_log") as _log:
        logger.LoggerWithSuccessAndOutput("foo").success("bar")
        _log.assert_called_once_with(logger.SUCCESS, "bar", ())


def test_output():
    with mock.patch.object(logger.LoggerWithSuccessAndOutput, "_log") as _log:
        logger.LoggerWithSuccessAndOutput("foo").output("bar")
        _log.assert_called_once_with(logger.OUTPUT, "bar", ())


def test_formatter(caplog):
    caplog.clear()
    logger.setup_logging(True, verbose=True)
    with caplog.at_level(logging.DEBUG):
        logger.logger.info("bar")
        logger.logger.output("foo")

    logs = [rec for rec in caplog.records if rec.levelname in ("INFO", "OUTPUT")]
    assert len(logs) == 1
    assert not hasattr(logs[0], "asctime")

    caplog.clear()
    with caplog.at_level(logger.OUTPUT):
        logger.logger.info("bar")
        logger.logger.output("foo")

    logs = [rec for rec in caplog.records if rec.levelname in ("INFO", "OUTPUT")]
    assert len(logs) == 2

    logs = [rec for rec in caplog.records if rec.levelname == "OUTPUT"]
    assert len(logs) == 1
    # Make sure output level log records are not nox prefixed
    assert "nox" not in logs[0].message


@pytest.mark.parametrize(
    "color",
    [
        # This currently fails due to some incompatibility between caplog and colorlog
        # that causes caplog to not collect the asctime from colorlog.
        pytest.param(True, id="color", marks=pytest.mark.xfail),
        pytest.param(False, id="no-color"),
    ],
)
def test_no_color_timestamp(caplog, color):
    logger.setup_logging(color=color, add_timestamp=True)
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        logger.logger.info("bar")
        logger.logger.output("foo")

    logs = [rec for rec in caplog.records if rec.levelname in ("INFO", "OUTPUT")]
    assert len(logs) == 1
    assert hasattr(logs[0], "asctime")

    caplog.clear()
    with caplog.at_level(logger.OUTPUT):
        logger.logger.info("bar")
        logger.logger.output("foo")

    logs = [rec for rec in caplog.records if rec.levelname != "OUTPUT"]
    assert len(logs) == 1
    assert hasattr(logs[0], "asctime")

    logs = [rec for rec in caplog.records if rec.levelname == "OUTPUT"]
    assert len(logs) == 1
    # no timestamp for output
    assert not hasattr(logs[0], "asctime")
