from __future__ import annotations

import datetime as dt

import nox


class Foo:
    pass


@nox.session(venv_backend="none")
@nox.parametrize(
    "arg",
    ["Jane", "Joe's", '"hello world"', dt.datetime(1980, 1, 1), [42], Foo()],
)
def test(session, arg):
    pass
