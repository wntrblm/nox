# Copyright 2020 Alethea Katherine Flowers
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

__all__ = ["TYPE_CHECKING", "ClassVar", "NoReturn", "Python"]

import typing as _typing

try:
    from typing import TYPE_CHECKING
except ImportError:
    try:
        from typing import TYPE_CHECKING
    except ImportError:
        TYPE_CHECKING = False

try:
    from typing import NoReturn
except ImportError:
    try:
        from typing import NoReturn
    except ImportError:
        pass


try:
    from typing import ClassVar
except ImportError:
    try:
        from typing import ClassVar
    except ImportError:
        pass

Python = _typing.Optional[_typing.Union[str, _typing.Sequence[str], bool]]
