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
import nox

# future version, to make sure error is logged and returned
needs_nox = "4001.1.1"

# the following session argument makes this entire file unimportable - during
# import, a TypeError would be raised:
# TypeError: session_decorator() got an unexpected keyword argument
@nox.session(there_is_no_such_parameter_in_current_version=True)
def dummy(session):
    pass
