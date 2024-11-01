from pathlib import Path

import nox

DIR = Path(__file__).parent.resolve()


@nox.session(venv_backend="none", default=False)
def orig(session: nox.Session) -> None:
    assert Path("orig_file.txt").exists()


@nox.session(venv_backend="none", default=False)
def sym(session: nox.Session) -> None:
    assert Path("sym_file.txt").exists()

    assert session.noxfile.resolve().parent.joinpath("orig_file.txt").exists()
