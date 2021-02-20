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

from typing import Optional

from nox._options import noxfile_options as options
from nox._parametrize import Param as param
from nox._parametrize import parametrize_decorator as parametrize
from nox.registry import session_decorator as session
from nox.sessions import Session

needs_version: Optional[str] = None

__all__ = ["needs_version", "parametrize", "param", "session", "options", "Session"]
