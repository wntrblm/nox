#!/usr/bin/env python

# /// script
# dependencies = ["nox", "cowsay"]
# ///


import nox


@nox.session
def exec_example(session: nox.Session) -> None:
    # Importing inside the function so that if the test fails,
    # it shows a better failure than immediately failing to import
    import cowsay  # noqa: PLC0415

    print(cowsay.cow("another_world"))


if __name__ == "__main__":
    nox.main()
