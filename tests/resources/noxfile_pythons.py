from __future__ import annotations

import nox


@nox.session(python=["3.6"])
@nox.session(name="other", python=["3.6"])
@nox.parametrize("cheese", ["cheddar", "jack", "brie"])
def snack(unused_session, cheese):
    print(f"Noms, {cheese} so good!")


@nox.session(python=False)
def nopy(unused_session):
    print("No pythons here.")


@nox.session(python="3.12")
def strpy(unused_session):
    print("Python-in-a-str here.")
