import nox


@nox.session
@nox.parametrize(
    ["version"],
    [["8.1.0"], ["7.5.0"]],
    ["8.1.0", "7.5.0"],
)
def check_package_files(session: nox.Session, version: str):
    pass
