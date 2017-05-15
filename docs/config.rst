Configuration
=============

Noxfile
-------

Nox looks for configuration in a file named `nox.py` by default. You can specify a different file using the ``--noxfile`` argument when running ``nox``.

Nox sessions are configured via standard Python functions that are decoratored with ``@nox.session`` or start with ``session_``. For example, these are all sessions::

    def session_a(session):
        pass

    def session_123(session):
        pass

    @nox.session
    def b(session):
        pass

These are **not**::

    def some_session(session):
        pass

    def other_func(session):
        pass


You may define sessions using either the decorator or the naming convention. There is one difference between these: if you use the decorator, then sessions will be run by nox in the order that they appear in the noxfile. If you define sessions using the naming convention, they run in alphabetical order.

If you mix and match the two methods, all sessions defined using the decorator are run first (in order), followed by all sessions defined by the naming convention, alphabetically.

SessionConfig object
--------------------

.. module:: nox.sessions

Nox will call your sessions functions with a :class:`SessionConfig` object.

.. autoclass:: SessionConfig
   :members:
