# Copyright 2016 Jon Wayne Parrott
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

from colorlog import ColoredFormatter

SUCCESS = 25


class LoggerWithSuccess(logging.getLoggerClass()):
    def __init__(self, name, level=logging.NOTSET):
        super(LoggerWithSuccess, self).__init__(name, level)
        logging.addLevelName(SUCCESS, "SUCCESS")

    def success(self, msg, *args, **kwargs):
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, msg, args, **kwargs)
        else:  # pragma: no cover
            pass


logging.setLoggerClass(LoggerWithSuccess)
logger = logging.getLogger('nox')
logger.setLevel(logging.DEBUG)


def setup_logging():  # pragma: no cover
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()

    formatter = ColoredFormatter(
        "%(cyan)s%(name)s > %(log_color)s%(message)s",
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'blue',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
            'SUCCESS': 'green'
        }
    )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Silence noisy loggers
    logging.getLogger('sh').setLevel(logging.WARNING)
