from __future__ import annotations

import nox

env = nox.env("tests")


# Tasks cannot parametrize python; building the manifest for this noxfile
# raises ValueError.
@env.task
@nox.parametrize("python", ["3.12"])
def run(unused_session):
    pass
