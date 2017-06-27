Configuration & API
===================

Noxfile
-------

Nox looks for configuration in a file named `nox.py` by default. You can specify
a different file using the ``--noxfile`` argument when running ``nox``.

Defining sessions
-----------------

.. autofunction:: nox.session

Nox sessions are configured via standard Python functions that are decorated
with ``@nox.session`` or start with ``session_``. For example, these are all
sessions::

    import nox

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

You may define sessions using either the decorator or the naming convention.
This can affect the execution order as described in the
:ref:`usage docs<session_execution_order>`.

You can also parametrize sessions as described in
:ref:`parametrized sessions <parametrized>`.

Configuring sessions
--------------------

.. module:: nox.sessions

Nox will call your session functions with a :class:`SessionConfig` object. You
use this object to tell nox how to create your session and which actions to
run. Session configuration is *declarative*, nox runs your session function
first to gather the list of things to do, then executes them separately.

.. autoclass:: SessionConfig
    :members:
    :undoc-members:
