from __future__ import annotations

import nox


@nox.session  # no tags
def no_tags(unused_session):
    print("Look ma, no tags!")


@nox.session(tags=["tag1"])
def one_tag(unused_session):
    print("Lonesome tag here.")


@nox.session(tags=["tag1", "tag2", "tag3"])
def more_tags(unused_session):
    print("Some more tags here.")


@nox.session(tags=["tag4"])
@nox.parametrize("foo", [nox.param(1, tags=["tag5", "tag6"])])
@nox.parametrize("bar", [2, 3], tags=[["tag7"]])
def parametrized_tags(unused_session):
    print("Parametrized tags here.")
