# Copyright 2016 Alethea Katherine Flowers
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
from typing import Any, cast

from colorlog import ColoredFormatter

SUCCESS = 25
OUTPUT = logging.DEBUG - 1


class NoxFormatter(ColoredFormatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(NoxFormatter, self).__init__(*args, **kwargs)
        self._simple_fmt = logging.Formatter("%(message)s")

    def format(self, record: Any) -> str:
        if record.levelname == "OUTPUT":
            return self._simple_fmt.format(record)
        return super(NoxFormatter, self).format(record)


class LoggerWithSuccessAndOutput(logging.getLoggerClass()):  # type: ignore
    def __init__(self, name: str, level: int = logging.NOTSET):
        super(LoggerWithSuccessAndOutput, self).__init__(name, level)
        logging.addLevelName(SUCCESS, "SUCCESS")
        logging.addLevelName(OUTPUT, "OUTPUT")

    def success(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, msg, args, **kwargs)
        else:  # pragma: no cover
            pass

    def output(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(OUTPUT):
            self._log(OUTPUT, msg, args, **kwargs)
        else:  # pragma: no cover
            pass


logging.setLoggerClass(LoggerWithSuccessAndOutput)
logger = cast(LoggerWithSuccessAndOutput, logging.getLogger("nox"))


def setup_logging(color: bool, verbose: bool = False) -> None:  # pragma: no cover
    """Setup logging.

    Args:
        color (bool): If true, the output will be colored using
            colorlog. Otherwise, it will be plaintext.
    """
    root_logger = logging.getLogger()
    if verbose:
        root_logger.setLevel(OUTPUT)
    else:
        root_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()

    if color is True:
        formatter = NoxFormatter(
            "%(cyan)s%(name)s > %(log_color)s%(message)s",
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "blue",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
                "SUCCESS": "green",
            },
        )

        handler.setFormatter(formatter)

    root_logger.addHandler(handler)

    # Silence noisy loggers
    logging.getLogger("sh").setLevel(logging.WARNING)
