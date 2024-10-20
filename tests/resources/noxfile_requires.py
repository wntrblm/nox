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

import nox


@nox.session(requires=["c", "b"])
def a(session):
    print(session.name)


@nox.session()
def b(session):
    print(session.name)


@nox.session()
def c(session):
    print(session.name)


@nox.session(requires=["e"])
def d(session):
    print(session.name)


@nox.session(requires=["c"])
def e(session):
    print(session.name)


@nox.session(requires=["b", "g"])
def f(session):
    print(session.name)


@nox.session(requires=["b", "h"])
def g(session):
    print(session.name)


@nox.session(requires=["c"])
def h(session):
    print(session.name)


@nox.session(requires=["j"])
def i(session):
    print(session.name)


@nox.session(requires=["i"])
def j(session):
    print(session.name)


@nox.session(python=["3.9", "3.10"])
def k(session):
    print(session.name)


@nox.session(requires=["k"])
def m(session):
    print(session.name)


@nox.session(python="3.10", requires=["k-{python}"])
def n(session):
    print(session.name)


@nox.session(requires=["does_not_exist"])
def o(session):
    print(session.name)


@nox.session(python=["3.9", "3.10"])
def p(session):
    print(session.name)


@nox.session(python=None, requires=["p-{python}"])
def q(session):
    print(session.name)


@nox.session
def r(session):
    print(session.name)
    raise Exception("Fail!")


@nox.session(requires=["r"])
def s(session):
    print(session.name)


@nox.session(requires=["r"])
def t(session):
    print(session.name)


@nox.parametrize("django", ["1.9", "2.0"])
@nox.session
def u(session, django):
    print(session.name)


@nox.session(requires=["u(django='1.9')", "u(django='2.0')"])
def v(session):
    print(session.name)


@nox.session(requires=["u"])
def w(session):
    print(session.name)
