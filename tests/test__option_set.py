# Copyright 2019 Alethea Katherine Flowers
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

import pytest

from nox import _option_set


# The vast majority of _option_set is tested by test_main, but the test helper
# :func:`OptionSet.namespace` needs a bit of help to get to full coverage.


class TestOptionSet:
    def test_namespace(self):
        optionset = _option_set.OptionSet()
        optionset.add_options(_option_set.Option("option_a", default="meep"))

        namespace = optionset.namespace()

        assert hasattr(namespace, "option_a")
        assert not hasattr(namespace, "non_existant_option")
        assert namespace.option_a == "meep"

    def test_namespace_values(self):
        optionset = _option_set.OptionSet()
        optionset.add_options(_option_set.Option("option_a", default="meep"))

        namespace = optionset.namespace(option_a="moop")

        assert namespace.option_a == "moop"

    def test_namespace_non_existant_options_with_values(self):
        optionset = _option_set.OptionSet()

        with pytest.raises(KeyError):
            optionset.namespace(non_existant_option="meep")
