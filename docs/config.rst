Configuration & API
===================

Noxfile
-------

Nox looks for configuration in a file named ``noxfile.py`` by default. You can specify
a different file using the ``--noxfile`` argument when running ``nox``.


Defining sessions
-----------------

.. autofunction:: nox.session

Nox sessions are configured via standard Python functions that are decorated
with ``@nox.session``. For example:

.. code-block:: python

    import nox

    @nox.session
    def tests(session):
        session.run('pytest')

You can also configure sessions to run against multiple Python versions as described in :ref:`virtualenv config` and  parametrize sessions as described in :ref:`parametrized sessions <parametrized>`.


Session description
-------------------

You can add a description to your session using a `docstring <https://www.python.org/dev/peps/pep-0257>`__.
The first line will be shown when listing the sessions. For example:

.. code-block:: python

    import nox

    @nox.session
    def tests(session):
        """Run the test suite."""
        session.run('pytest')

The ``nox --list`` command will show:

.. code-block:: console

    $ nox --list
    Available sessions:
    * tests -> Run the test suite.


Session name
------------

By default Nox uses the decorated function's name as the session name. This works wonderfully for the vast majority of projects, however, if you need to you can customize the session's name by using the ``name`` argument to ``@nox.session``. For example:

.. code-block:: python

    import nox

    @nox.session(name="custom-name")
    def a_very_long_function_name(session):
        print("Hello!")


The ``nox --list`` command will show:

.. code-block:: console

    $ nox --list
    Available sessions:
    * custom-name

And you can tell ``nox`` to run the session using the custom name:

.. code-block:: console

    $ nox --session "custom-name"
    Hello!


.. _virtualenv config:

Configuring a session's virtualenv
----------------------------------

By default, Nox will create a new virtualenv for each session using the same interpreter that Nox uses. If you installed Nox using Python 3.6, Nox will use Python 3.6 by default for all of your sessions.

You can tell Nox to use a different Python interpreter/version by specifying the ``python`` argument (or its alias ``py``) to ``@nox.session``:

.. code-block:: python

    @nox.session(python='2.7')
    def tests(session):
        pass

.. note::

    The Python binaries on Windows are found via the Python `Launcher`_ for
    Windows (``py``). For example, Python 3.9 can be found by determining which
    executable is invoked by ``py -3.9``. If a given test needs to use the 32-bit
    version of a given Python, then ``X.Y-32`` should be used as the version.

    .. _Launcher: https://docs.python.org/3/using/windows.html#python-launcher-for-windows

You can also tell Nox to run your session against multiple Python interpreters. Nox will create a separate virtualenv and run the session for each interpreter you specify. For example, this session will run twice - once for Python 2.7 and once for Python 3.6:

.. code-block:: python

    @nox.session(python=['2.7', '3.6'])
    def tests(session):
        pass

When you provide a version number, Nox automatically prepends python to determine the name of the executable. However, Nox also accepts the full executable name. If you want to test using pypy, for example:

.. code-block:: python

    @nox.session(python=['2.7', '3.6', 'pypy-6.0'])
    def tests(session):
        pass

When collecting your sessions, Nox will create a separate session for each interpreter. You can see these sessions when running ``nox --list``. For example this Noxfile:

.. code-block:: python

    @nox.session(python=['2.7', '3.6', '3.7', '3.8', '3.9'])
    def tests(session):
        pass

Will produce these sessions:

.. code-block:: console

    * tests-2.7
    * tests-3.6
    * tests-3.7
    * tests-3.8
    * tests-3.9

Note that this expansion happens *before* parameterization occurs, so you can still parametrize sessions with multiple interpreters.

If you want to disable virtualenv creation altogether, you can set ``python`` to ``False``, or set ``venv_backend`` to ``"none"``, both are equivalent. Note that this can be done temporarily through the :ref:`--no-venv <opt-force-venv-backend>` commandline flag, too.

.. code-block:: python

    @nox.session(python=False)
    def tests(session):
        pass

You can also specify that the virtualenv should *always* be reused instead of recreated every time:

.. code-block:: python

    @nox.session(
        python=['2.7', '3.6'],
        reuse_venv=True)
    def tests(session):
        pass

You are not limited to virtualenv, there is a selection of backends you can choose from as venv, conda or virtualenv (default):

.. code-block:: python

    @nox.session(venv_backend='venv')
    def tests(session):
        pass

Finally, custom backend parameters are supported:

.. code-block:: python

    @nox.session(venv_params=['--no-download'])
    def tests(session):
        pass


Passing arguments into sessions
-------------------------------

Often it's useful to pass arguments into your test session. Here's a quick
example that demonstrates how to use arguments to run tests against a
particular file:

.. code-block:: python

    @nox.session
    def test(session):
        session.install('pytest')

        if session.posargs:
            test_files = session.posargs
        else:
            test_files = ['test_a.py', 'test_b.py']

        session.run('pytest', *test_files)

Now you if you run:


.. code-block:: console

    nox


Then nox will run:

.. code-block:: console

    pytest test_a.py test_b.py


But if you run:

.. code-block:: console

    nox -- test_c.py


Then nox will run:

.. code-block:: console

    pytest test_c.py


.. _parametrized:

Parametrizing sessions
----------------------

Session arguments can be parametrized with the :func:`nox.parametrize` decorator. Here's a typical example of parametrizing the Django version to install:

.. code-block:: python

    @nox.session
    @nox.parametrize('django', ['1.9', '2.0'])
    def tests(session, django):
        session.install(f'django=={django}')
        session.run('pytest')

When you run ``nox``, it will create a two distinct sessions:

.. code-block:: console

    $ nox
    nox > Running session tests(django='1.9')
    nox > python -m pip install django==1.9
    ...
    nox > Running session tests(django='2.0')
    nox > python -m pip install django==2.0


:func:`nox.parametrize` has an interface and usage intentionally similar to `pytest's parametrize <https://pytest.org/latest/parametrize.html#_pytest.python.Metafunc.parametrize>`_.

.. autofunction:: nox.parametrize

You can also stack the decorator to produce sessions that are a combination of the arguments, for example:

.. code-block:: python

    @nox.session
    @nox.parametrize('django', ['1.9', '2.0'])
    @nox.parametrize('database', ['postgres', 'mysql'])
    def tests(session, django, database):
        ...


If you run ``nox --list``, you'll see that this generates the following set of sessions:

.. code-block:: console

    * tests(database='postgres', django='1.9')
    * tests(database='mysql', django='1.9')
    * tests(database='postgres', django='2.0')
    * tests(database='mysql', django='2.0')


If you only want to run one of the parametrized sessions, see :ref:`running_paramed_sessions`.


Giving friendly names to parametrized sessions
----------------------------------------------

The automatically generated names for parametrized sessions, such as ``tests(django='1.9', database='postgres')``, can be long and unwieldy to work with even with using :ref:`keyword filtering <opt-sessions-pythons-and-keywords>`. You can give parametrized sessions custom IDs to help in this scenario. These two examples are equivalent:

.. code-block:: python

    @nox.session
    @nox.parametrize('django',
        ['1.9', '2.0'],
        ids=['old', 'new'])
    def tests(session, django):
        ...

.. code-block:: python

    @nox.session
    @nox.parametrize('django', [
        nox.param('1.9', id='old'),
        nox.param('2.0', id='new'),
    ])
    def tests(session, django):
        ...

When running ``nox --list`` you'll see their new IDs:

.. code-block:: console

    * tests(old)
    * tests(new)

And you can run them with ``nox --sessions "tests(old)"`` and so on.

This works with stacked parameterizations as well. The IDs are combined during the combination. For example:

.. code-block:: python

    @nox.session
    @nox.parametrize(
        'django',
        ['1.9', '2.0'],
        ids=["old", "new"])
    @nox.parametrize(
        'database',
        ['postgres', 'mysql'],
        ids=["psql", "mysql"])
    def tests(session, django, database):
        ...

Produces these sessions when running ``nox --list``:

.. code-block:: console

    * tests(psql, old)
    * tests(mysql, old)
    * tests(psql, new)
    * tests(mysql, new)


The session object
------------------

.. module:: nox.sessions

Nox will call your session functions with a an instance of the :class:`Session`
class.

.. autoclass:: Session
    :members:
    :undoc-members:


Modifying Nox's behavior in the Noxfile
---------------------------------------

Nox has various :doc:`command line arguments <usage>` that can be used to modify its behavior. Some of these can also be specified in the Noxfile using ``nox.options``. For example, if you wanted to store Nox's virtualenvs in a different directory without needing to pass it into ``nox`` every time:

.. code-block:: python

    import nox

    nox.options.envdir = ".cache"

    @nox.session
    def tests(session):
        ...

Or, if you wanted to provide a set of sessions that are run by default:

.. code-block:: python

    import nox

    nox.options.sessions = ["lint", "tests-3.6"]

    ...

The following options can be specified in the Noxfile:

* ``nox.options.envdir`` is equivalent to specifying :ref:`--envdir <opt-envdir>`.
* ``nox.options.sessions`` is equivalent to specifying :ref:`-s or --sessions <opt-sessions-pythons-and-keywords>`.
* ``nox.options.pythons`` is equivalent to specifying :ref:`-p or --pythons <opt-sessions-pythons-and-keywords>`.
* ``nox.options.keywords`` is equivalent to specifying :ref:`-k or --keywords <opt-sessions-pythons-and-keywords>`.
* ``nox.options.default_venv_backend`` is equivalent to specifying :ref:`-db or --default-venv-backend <opt-default-venv-backend>`.
* ``nox.options.force_venv_backend`` is equivalent to specifying :ref:`-fb or --force-venv-backend <opt-force-venv-backend>`.
* ``nox.options.reuse_existing_virtualenvs`` is equivalent to specifying :ref:`--reuse-existing-virtualenvs <opt-reuse-existing-virtualenvs>`. You can force this off by specifying ``--no-reuse-existing-virtualenvs`` during invocation.
* ``nox.options.stop_on_first_error`` is equivalent to specifying :ref:`--stop-on-first-error <opt-stop-on-first-error>`. You can force this off by specifying ``--no-stop-on-first-error`` during invocation.
* ``nox.options.error_on_missing_interpreters`` is equivalent to specifying :ref:`--error-on-missing-interpreters <opt-error-on-missing-interpreters>`. You can force this off by specifying ``--no-error-on-missing-interpreters`` during invocation.
* ``nox.options.error_on_external_run`` is equivalent to specifying :ref:`--error-on-external-run <opt-error-on-external-run>`. You can force this off by specifying ``--no-error-on-external-run`` during invocation.
* ``nox.options.report`` is equivalent to specifying :ref:`--report <opt-report>`.


When invoking ``nox``, any options specified on the command line take precedence over the options specified in the Noxfile. If either ``--sessions`` or ``--keywords`` is specified on the command line, *both* options specified in the Noxfile will be ignored.


Nox version requirements
------------------------

Nox version requirements can be specified in your Noxfile by setting
``nox.needs_version``. If the Nox version does not satisfy the requirements, Nox
exits with a friendly error message. For example:

.. code-block:: python

    import nox

    nox.needs_version = ">=2019.5.30"

    @nox.session(name="test")  # name argument was added in 2019.5.30
    def pytest(session):
        session.run("pytest")

Any of the version specifiers defined in `PEP 440`_ can be used.

.. warning:: Version requirements *must* be specified as a string literal,
    using a simple assignment to ``nox.needs_version`` at the module level. This
    allows Nox to check the version without importing the Noxfile.

.. _PEP 440: https://www.python.org/dev/peps/pep-0440/
