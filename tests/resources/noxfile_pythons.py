from __future__ import annotations

import nox


@nox.session(python=["3.6"])
@nox.parametrize("cheese", ["cheddar", "jack", "brie"])
def snack(unused_session, cheese):
    print(f"Noms, {cheese} so good!")
