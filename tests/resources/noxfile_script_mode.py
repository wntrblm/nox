# /// script
# dependencies = ["nox", "cowsay"]
# ///

import cowsay

import nox


@nox.session
def example(session: nox.Session) -> None:
    print(cowsay.cow("hello_world"))
