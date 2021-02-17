# Copyright 2021 Alethea Katherine Flowers
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

from nox import needs_version
from nox._version import get_nox_version



def test_needs_version_default() -> None:
    """It is None by default."""
    assert needs_version is None


def test_get_nox_version() -> None:
    """It returns something that looks like a Nox version."""
    result = get_nox_version()
    year, month, day = [int(part) for part in result.split(".")[:3]]
    assert year >= 2020
