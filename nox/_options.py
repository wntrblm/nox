# Copyright 2018 Alethea Katherine Flowers
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


class options:
    """Options that are configurable in the Noxfile.

    By setting properties on ``nox.options`` you can specify command line
    arguments in your Noxfile. If an argument is specified in both the Noxfile
    and on the command line, the command line arguments take precedence.

    See :doc:`usage` for more details on these settings and their effect.
    """

    sessions = None
    keywords = None
    envdir = None
    reuse_existing_virtualenvs = False
    stop_on_first_error = False
    error_on_missing_interpreters = False
    error_on_external_run = False
    report = None
