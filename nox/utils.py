# Copyright 2017 Jon Wayne Parrott
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

import six


def coerce_str(maybe_str):
    """Returns a str object, on both Python 2 and Python 3.

    This means that Python 2 gets a bytes, and Python 3 gets a Unicode
    text string.

    This is what is expected for environment variables, where sending a
    unicode on Python 2 or a bytes on Python 3 will raise an exception.
    """
    # If we already have a string, we are done.
    if isinstance(maybe_str, str):
        return maybe_str

    # On Python 2, we got a unicode; on Python 3, we got a bytes.
    if six.PY2:
        return maybe_str.encode('utf-8')
    return maybe_str.decode('utf-8')
