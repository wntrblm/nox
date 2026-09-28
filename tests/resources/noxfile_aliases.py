from __future__ import annotations

import nox

tooling = nox.env("tooling", venv_backend="none")


@tooling.task
def lint(session: nox.Session) -> None:
    pass


@tooling.task
def fmt(session: nox.Session) -> None:
    pass


nox.alias("check", "tooling:lint", "tooling:fmt")
