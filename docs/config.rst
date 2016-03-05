Configuration
=============

Noxfile
-------

Nox looks for configuration in a file named `nox.py` by default. You can specify a different file using the ``--noxfile`` argument when running ``nox``.

Nox sessions are configured via standard Python functions that start with ``session_``. For example, these are all sessions::

    def session_a(session):
        pass

    def session_123(session):
        pass

These are **not**::

    def some_session(session):
        pass

    def other_func(session):
        pass


SessionConfig object
--------------------

.. module:: nox.session

Nox will call your sessions functions with a :class:`SessionConfig` object.

.. autoclass:: SessionConfig
   :members:
