Configuration & API
===================

Noxfile
-------

Nox looks for configuration in a file named `noxfile.py` by default. You can specify
a different file using the ``--noxfile`` argument when running ``nox``.

Defining sessions
-----------------

.. autofunction:: nox.session

Nox sessions are configured via standard Python functions that are decorated
with ``@nox.session``. For example::

    import nox

    @nox.session
    def tests(session):
        session.run('pytest')

You can also configure sessions to run against multiple Python versions as described in :ref:`virtualenv config` and  parametrize sessions as described in :ref:`parametrized sessions <parametrized>`.


Session description
-------------------

You can add a description to your session using a `docstring <https://www.python.org/dev/peps/pep-0257>`__.
The first line will be shown when listing the sessions. For example::

    import nox

    @nox.session
    def tests(session):
        """Run the test suite."""
        session.run('pytest')

The ``nox -l`` command will show:

.. code-block:: console

    $ nox -l
    Available sessions:
    * tests -> Run the test suite.

.. _virtualenv config:

Configuring a session's virtualenv
----------------------------------

By default, Nox will create a new virtualenv for each session using the same interpreter that Nox uses. If you installed Nox using Python 3.6, Nox will use Python 3.6 by default for all of your sessions.

You can tell Nox to use a different Python interpreter/version by specifying the ``python``  argument (or its alias ``py``) to ``@nox.session``::

    @nox.session(python='2.7')
    def tests(session):
        pass

You can also tell Nox to run your session against multiple Python interpreters. Nox will create a separate virtualenv and run the session for each interpreter you specify. For example, this session will run twice - once for Python 2.7 and once for Python 3.6::

    @nox.session(python=['2.7', '3.6'])
    def tests(session):
        pass

When you provide a version number, Nox automatically prepends python to determine the name of the executable. However, Nox also accepts the full executable name. If you want to test using pypy, for example::

    @nox.session(python=['2.7', '3.6', 'pypy-6.0'])
    def tests(session):
        pass

When collecting your sessions, Nox will create a separate session for each interpreter. You can see these sesions when running ``nox --list-sessions``. For example this Noxfile::

    @nox.session(python=['2.7', '3.5', '3.6', '3.7'])
    def tests(session):
        pass

Will produce these sessions::

    * tests-2.7
    * tests-3.5
    * tests-3.6
    * tests-3.7

Note that this expansion happens *before* parameterization occurs, so you can still parametrize sessions with multiple interpreters.

If you want to disable virtualenv creation altogether, you can set ``python`` to ``False``::

    @nox.session(python=False)
    def tests(session):
        pass

Finally you can also specify that the virtualenv should *always* be reused instead of recreated every time::

    @nox.session(
        python=['2.7', '3.6'],
        reuse_venv=True)
    def tests(session):
        pass


Using the session object
------------------------

.. module:: nox.sessions

Nox will call your session functions with a :class:`Session` object. You use this object to to run various commands in your session.

.. autoclass:: Session
    :members:
    :undoc-members:
