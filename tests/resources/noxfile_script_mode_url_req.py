# /// script
# dependencies = ["nox @ git+https://github.com/wntrblm/nox.git@2024.10.09"]
# ///

# The Nox version pinned above should be the second-most-recent version or older.

import importlib.metadata

import nox


@nox.session(python=False)
def example(session: nox.Session) -> None:
    print(importlib.metadata.version("nox"))
