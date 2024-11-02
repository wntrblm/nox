from pathlib import Path

import nox

FILE = Path(__file__).resolve()


@nox.session(venv_backend="none", default=False)
def orig(session: nox.Session) -> None:
    assert Path("orig_file.txt").exists()


@nox.session(venv_backend="none", default=False)
def sym(session: nox.Session) -> None:
    assert Path("sym_file.txt").exists()

    assert FILE.parent.joinpath("orig_file.txt").exists()
