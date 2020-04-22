import nox


@nox.session(python=["3.6"])
@nox.parametrize("cheese", ["cheddar", "jack", "brie"])
def snack(unused_session, cheese):
    print("Noms, {} so good!".format(cheese))
