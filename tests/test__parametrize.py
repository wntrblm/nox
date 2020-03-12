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

from unittest import mock

import pytest
from nox import _decorators, _parametrize


@pytest.mark.parametrize(
    "param, other, expected",
    [
        (_parametrize.Param(1, 2), _parametrize.Param(1, 2), True),
        (_parametrize.Param(1, 2, id="a"), _parametrize.Param(1, 2, id="a"), True),
        (_parametrize.Param(1, 3), _parametrize.Param(1, 2), False),
        (_parametrize.Param(1, 2, arg_names=("a", "b")), {"a": 1, "b": 2}, True),
    ],
)
def test_param_eq(param, other, expected):
    assert (param == other) is expected


def test_param_eq_fail():
    with pytest.raises(NotImplementedError):
        _parametrize.Param() == "a"


def test_parametrize_decorator_one():
    def f():
        pass

    _parametrize.parametrize_decorator("abc", 1)(f)

    assert f.parametrize == [_parametrize.Param(1, arg_names=("abc",))]


def test_parametrize_decorator_one_param():
    def f():
        pass

    _parametrize.parametrize_decorator("abc", _parametrize.Param(1))(f)

    assert f.parametrize == [_parametrize.Param(1, arg_names=("abc",))]


def test_parametrize_decorator_one_with_args():
    def f():
        pass

    _parametrize.parametrize_decorator("abc", [1, 2, 3])(f)

    assert f.parametrize == [{"abc": 1}, {"abc": 2}, {"abc": 3}]


def test_parametrize_decorator_param():
    def f():
        pass

    _parametrize.parametrize_decorator(["abc", "def"], _parametrize.Param(1))(f)

    assert f.parametrize == [_parametrize.Param(1, arg_names=("abc", "def"))]


def test_parametrize_decorator_id_list():
    def f():
        pass

    _parametrize.parametrize_decorator("abc", [1, 2, 3], ids=["a", "b", "c"])(f)

    arg_names = ("abc",)
    assert f.parametrize == [
        _parametrize.Param(1, arg_names=arg_names, id="a"),
        _parametrize.Param(2, arg_names=arg_names, id="b"),
        _parametrize.Param(3, arg_names=arg_names, id="c"),
    ]


def test_parametrize_decorator_multiple_args_as_list():
    def f():
        pass

    _parametrize.parametrize_decorator(["abc", "def"], [("a", 1), ("b", 2), ("c", 3)])(
        f
    )

    assert f.parametrize == [
        {"abc": "a", "def": 1},
        {"abc": "b", "def": 2},
        {"abc": "c", "def": 3},
    ]


def test_parametrize_decorator_multiple_args_as_string():
    def f():
        pass

    _parametrize.parametrize_decorator("abc, def", [("a", 1), ("b", 2), ("c", 3)])(f)

    assert f.parametrize == [
        {"abc": "a", "def": 1},
        {"abc": "b", "def": 2},
        {"abc": "c", "def": 3},
    ]


def test_parametrize_decorator_mixed_params():
    def f():
        pass

    _parametrize.parametrize_decorator(
        "abc, def", [(1, 2), _parametrize.Param(3, 4, id="b"), _parametrize.Param(5, 6)]
    )(f)

    arg_names = ("abc", "def")
    assert f.parametrize == [
        _parametrize.Param(1, 2, arg_names=arg_names),
        _parametrize.Param(3, 4, arg_names=arg_names, id="b"),
        _parametrize.Param(5, 6, arg_names=arg_names),
    ]


def test_parametrize_decorator_stack():
    def f():
        pass

    _parametrize.parametrize_decorator("abc", [1, 2, 3])(f)
    _parametrize.parametrize_decorator("def", ["a", "b"])(f)

    assert f.parametrize == [
        {"abc": 1, "def": "a"},
        {"abc": 2, "def": "a"},
        {"abc": 3, "def": "a"},
        {"abc": 1, "def": "b"},
        {"abc": 2, "def": "b"},
        {"abc": 3, "def": "b"},
    ]


def test_parametrize_decorator_multiple_and_stack():
    def f():
        pass

    _parametrize.parametrize_decorator("abc, def", [(1, "a"), (2, "b")])(f)
    _parametrize.parametrize_decorator("foo", ["bar", "baz"])(f)

    assert f.parametrize == [
        {"abc": 1, "def": "a", "foo": "bar"},
        {"abc": 2, "def": "b", "foo": "bar"},
        {"abc": 1, "def": "a", "foo": "baz"},
        {"abc": 2, "def": "b", "foo": "baz"},
    ]


def test_generate_calls_simple():

    f = mock.Mock()
    f.__name__ = "f"
    f.some_prop = 42

    arg_names = ("abc",)
    call_specs = [
        _parametrize.Param(1, arg_names=arg_names),
        _parametrize.Param(2, arg_names=arg_names),
        _parametrize.Param(3, arg_names=arg_names),
    ]

    calls = _decorators.Call.generate_calls(f, call_specs)

    assert len(calls) == 3
    assert calls[0].session_signature == "(abc=1)"
    assert calls[1].session_signature == "(abc=2)"
    assert calls[2].session_signature == "(abc=3)"

    calls[0]()
    f.assert_called_with(abc=1)
    calls[1]()
    f.assert_called_with(abc=2)
    calls[2]()
    f.assert_called_with(abc=3)

    # Make sure wrapping was done correctly.
    for call in calls:
        assert call.some_prop == 42
        assert call.__name__ == "f"


def test_generate_calls_multiple_args():

    f = mock.Mock()
    f.__name__ = "f"

    arg_names = ("abc", "foo")
    call_specs = [
        _parametrize.Param(1, "a", arg_names=arg_names),
        _parametrize.Param(2, "b", arg_names=arg_names),
        _parametrize.Param(3, "c", arg_names=arg_names),
    ]

    calls = _decorators.Call.generate_calls(f, call_specs)

    assert len(calls) == 3
    assert calls[0].session_signature == "(abc=1, foo='a')"
    assert calls[1].session_signature == "(abc=2, foo='b')"
    assert calls[2].session_signature == "(abc=3, foo='c')"

    calls[0]()
    f.assert_called_with(abc=1, foo="a")
    calls[1]()
    f.assert_called_with(abc=2, foo="b")
    calls[2]()
    f.assert_called_with(abc=3, foo="c")


def test_generate_calls_ids():
    f = mock.Mock()
    f.__name__ = "f"

    arg_names = ("foo",)
    call_specs = [
        _parametrize.Param(1, arg_names=arg_names, id="a"),
        _parametrize.Param(2, arg_names=arg_names, id="b"),
    ]

    calls = _decorators.Call.generate_calls(f, call_specs)

    assert len(calls) == 2
    assert calls[0].session_signature == "(a)"
    assert calls[1].session_signature == "(b)"

    calls[0]()
    f.assert_called_with(foo=1)
    calls[1]()
    f.assert_called_with(foo=2)
