# Copyright 2022 Alethea Katherine Flowers
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

import pytest

from nox._resolver import CycleError, lazy_stable_topo_sort


@pytest.mark.parametrize(
    ("dependencies", "expected"),
    [
        # Assert typical example with the following features:
        # 1.  Topological sort.
        # 2.  Ignores nodes outside the subgraph of ``dependencies[root]`` and its
        #     (recursive) dependencies. (``"f"`` and ``"g"``).
        # 3.  Lazy (``"e"`` does not occur any earlier than it needs to for ``"d"``).
        # 4.  Obeys ``dependencies[node]`` order preference when possible (``"a"`` and
        #     ``"d"``, ``"c"`` and ``"b"``).
        (
            {
                "a": ("c", "b"),
                "b": (),
                "c": (),
                "d": ("e",),
                "e": ("c",),
                "f": ("b", "g"),
                "g": (),
                "0": ("a", "d"),
            },
            ("c", "b", "a", "e", "d"),
        ),
        # 1.  Topological sort.
        # 2.  Ignores (``"f"`` and ``"g"``).
        # 3.  Lazy (``"b"``).
        # 4.  Obeys order preference (``"d"`` and ``"a"``).
        # 4.  Obeys order preference (``"c"`` and ``"b"``).
        (
            {
                "a": ("c", "b"),
                "b": (),
                "c": (),
                "d": ("e",),
                "e": ("c",),
                "f": ("b", "g"),
                "g": (),
                "0": ("d", "a"),
            },
            ("c", "e", "d", "b", "a"),
        ),
        # 1.  Topological sort.
        # 2.  Ignores (``"f"`` and ``"g"``).
        # 4.  Ignores order preference (``"a"`` and ``"d"``) when it is impossible to
        #     both satisfy a pair preference and produce a producing a topological and
        #     lazy sort.
        (
            {
                "a": ("d",),
                "b": (),
                "c": (),
                "d": ("e",),
                "e": ("c",),
                "f": ("b", "g"),
                "g": (),
                "0": ("a", "d"),
            },
            ("c", "e", "d", "a"),
        ),
        # 1.  Topological sort.
        # 2.  Ignores (``"f"`` and ``"g"``).
        # 3.  Lazy (``"e"``).
        # 4.  Obeys order preference (``"a"`` and ``"d"``).
        # 4.  Ignores order preference (``"c"`` and ``"b"``).
        (
            {
                "a": ("c", "b"),
                "b": (),
                "c": ("b",),
                "d": ("e",),
                "e": ("c",),
                "f": ("b",),
                "0": ("a", "d"),
            },
            ("b", "c", "a", "e", "d"),
        ),
        # 1.  Topological sort.
        # 2.  Ignores (``"f"``).
        # 3.  Lazy (``"c"``, ``"h"``, ``"a"``, and ``"e"``).
        # 4.  Obeys order preference (``"g"``, ``"a"``, and ``"d"``).
        # 4.  Obeys order preference (``"b"`` and ``"g"``).
        # 4.  Obeys order preference (``"b"`` and ``"h"``).
        # 4.  Ignores order preference (``"c"`` and ``"b"``). Note that this is despite
        #     the fact that the topological order between ``"b"`` and ``"c"`` is
        #     undefined. In the tests above, we only saw a pair order preference ignored
        #     because the topological order between that pair was defined. Here,
        #     however, the ``dependencies["a"]`` order preference between ``"b"`` and
        #     ``"c"`` is ignored because obeying this order preference cannot be done
        #     without making the sort non-lazy (here, calling ``"c"`` earlier than is
        #     required by one of its dependents (``"h"``) would be non-lazy).
        (
            {
                "a": ("c", "b"),
                "b": (),
                "c": (),
                "d": ("e",),
                "e": ("c",),
                "f": ("b", "g"),
                "g": ("b", "h"),
                "h": ("c",),
                "0": ("g", "a", "d"),
            },
            ("b", "c", "h", "g", "a", "e", "d"),
        ),
    ],
)
def test_lazy_stable_topo_sort(
    dependencies: dict[str, tuple[str, ...]], expected: tuple[str, ...]
) -> None:
    actual = tuple(lazy_stable_topo_sort(dependencies, "0"))
    actual_with_root = tuple(lazy_stable_topo_sort(dependencies, "0", drop_root=False))
    assert actual == actual_with_root[:-1] == expected


@pytest.mark.parametrize(
    ("dependencies", "expected_cycle"),
    [
        # Note that these cycles are inherent to the dependency graph; they cannot be
        # resolved by ignoring the order preference for a pair in ``dependencies[node]``
        # for some ``node``.
        (
            {
                "a": ("b",),
                "b": ("a",),
                "0": ("a",),
            },
            ("a", "b", "a"),
        ),
        (
            {
                "a": ("c", "b"),
                "b": (),
                "c": ("a", "b"),
                "0": ("a",),
            },
            ("a", "c", "a"),
        ),
    ],
)
def test_lazy_stable_topo_sort_CycleError(
    dependencies: dict[str, tuple[str, ...]], expected_cycle: tuple[str, ...]
) -> None:
    with pytest.raises(CycleError) as exc_info:
        tuple(lazy_stable_topo_sort(dependencies, "0"))
    # While the exact cycle reported is not unique and is an implementation detail, this
    # still serves as a regression test for unexpected changes in the implementation's
    # behavior.
    assert exc_info.value.args[1] == expected_cycle
