import nox


@nox.session(name="foo")
def a(session: nox.Session):
    print("a!")


@nox.session(name="foo")
def b(session: nox.Session):
    print("b!")
