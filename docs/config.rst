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

By default, all sessions will be run if no sessions are specified. You can
remove sessions from this default list by passing ``default=False`` in the
``@nox.session(...)`` decorator. You can also specify a list of sessions to run by
default using the ``nox.options.sessions = [...]`` configuration option.

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

If the specified python interpreter is not found, Nox can automatically download it when ``--download-python`` is set to ``auto`` (the default) or ``always``. ``never`` avoids the download.

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

Use of :func:`session.install()` is deprecated without a virtualenv since it modifies the global Python environment. If this is what you really want, use :func:`session.run()` and pip instead.

.. code-block:: python

    @nox.session(python=False)
    def tests(session):
        session.run("pip", "install", "nox")

You can also specify that the virtualenv should *always* be reused instead of recreated every time unless ``--reuse-venv=never``:

.. code-block:: python

    @nox.session(
        python=['2.7', '3.6'],
        reuse_venv=True)
    def tests(session):
        pass

You are not limited to virtualenv, there is a selection of backends you can choose from as venv, uv, conda, mamba, micromamba, or virtualenv (default):

.. code-block:: python

    @nox.session(venv_backend='venv')
    def tests(session):
        pass

You can chain together optional backends with ``|``, such as ``uv|virtualenv``
or ``micromamba|mamba|conda``, and the first available backend will be selected.
You cannot put anything after a backend that can't be missing like ``venv`` or
``virtualenv``.

Finally, custom backend parameters are supported:

.. code-block:: python

    @nox.session(venv_params=['--no-download'])
    def tests(session):
        pass

If you need to check to see which backend was selected, you can access it via
``session.venv_backend``.


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


Parametrizing the session Python
--------------------------------

You can use parametrization to select the Python interpreter for a session.
These two examples are equivalent:

.. code-block:: python

    @nox.session
    @nox.parametrize("python", ["3.10", "3.11", "3.12"])
    def tests(session):
        ...

    @nox.session(python=["3.10", "3.11", "3.12"])
    def tests(session):
        ...

The first form can be useful if you need to exclude some combinations of Python
versions with other parameters. For example, you may want to test against
multiple versions of a dependency, but the latest version doesn't run on older
Pythons:

.. code-block:: python

    @nox.session
    @nox.parametrize(
        "python,dependency",
        [
            (python, dependency)
            for python in ("3.10", "3.11", "3.12")
            for dependency in ("1.0", "2.0")
            if (python, dependency) != ("3.10", "2.0")
        ],
    )
    def tests(session, dependency):
        ...


Assigning tags to parametrized sessions
---------------------------------------

Just as tags can be :ref:`assigned to normal sessions <session tags>`, they can also be assigned to parametrized sessions.  The following examples are both equivalent:

.. code-block:: python

    @nox.session
    @nox.parametrize('dependency',
        ['1.0', '2.0'],
        tags=[['old'], ['new']])
    @nox.parametrize('database'
        ['postgres', 'mysql'],
        tags=[['psql'], ['mysql']])
    def tests(session, dependency, database):
        ...

.. code-block:: python

    @nox.session
    @nox.parametrize('dependency', [
        nox.param('1.0', tags=['old']),
        nox.param('2.0', tags=['new']),
    ])
    @nox.parametrize('database', [
        nox.param('postgres', tags=['psql']),
        nox.param('mysql', tags=['mysql']),
    ])
    def tests(session, dependency, database):
        ...

In either case, running ``nox --tags old`` will run the tests using version 1.0 of the dependency against both database backends, while running ``nox --tags psql`` will run the tests using both versions of the dependency, but only against PostgreSQL.

More sophisticated tag assignment can be performed by passing a generator to the ``@nox.parametrize`` decorator, as seen in the following example:

.. code-block:: python

    def generate_params():
        for dependency in ["1.0", "1.1", "2.0"]:
            for database in ["sqlite", "postgresql", "mysql"]:
                tags = []
                if dependency == "2.0" and database == "sqlite":
                    tags.append("quick")
                if dependency == "2.0" or database == "sqlite":
                    tags.append("standard")
                yield nox.param(dependency, database, tags=tags)

    @nox.session
    @nox.parametrize(["dependency", "database"], generate_params())
    def tests(session, dependency, database):
        ...

In this example, the ``quick`` tag is assigned to the single combination of the latest version of the dependency along with the SQLite database backend, allowing a developer to run the tests in a single configuration as a basic sanity test.  The ``standard`` tag, in contrast, selects combinations targeting either the latest version of the dependency *or* the SQLite database backend.  If the developer runs ``tox --tags standard``, the tests will be run against all supported versions of the dependency with the SQLite backend, as well as against all supported database backends under the latest version of the dependency, giving much more comprehensive test coverage while using only five of the potential nine test matrix combinations.


The session object
------------------

.. module:: nox.sessions

Nox will call your session functions with an instance of the :class:`Session`
class.

.. autoclass:: Session
    :members:
    :undoc-members:

The pyproject.toml helpers
--------------------------

Nox provides helpers for ``pyproject.toml`` projects in the ``nox.project`` namespace.

.. automodule:: nox.project
   :members:

Modifying Nox's behavior in the Noxfile
---------------------------------------

Nox has various :doc:`command line arguments <usage>` that can be used to modify its behavior. Some of these can also be specified in the Noxfile using ``nox.options``. For example, if you wanted to store Nox's virtualenvs in a different directory without needing to pass it into ``nox`` every time:

.. code-block:: python

    import nox

    nox.options.envdir = ".cache"

    @nox.session
    def tests(session):
        ...

Or, if you wanted to provide a set of sessions that are run by default (this overrides the ``default=`` argument to sessions):

.. code-block:: python

    import nox

    nox.options.sessions = ["lint", "tests-3.6"]

    ...

The following options can be specified in the Noxfile:

* ``nox.options.envdir`` is equivalent to specifying :ref:`--envdir <opt-envdir>`.
* ``nox.options.sessions`` is equivalent to specifying :ref:`-s or --sessions <opt-sessions-pythons-and-keywords>`. If set to an empty list, no sessions will be run if no sessions were given on the command line, and the list of available sessions will be shown instead.
* ``nox.options.pythons`` is equivalent to specifying :ref:`-p or --pythons <opt-sessions-pythons-and-keywords>`.
* ``nox.options.keywords`` is equivalent to specifying :ref:`-k or --keywords <opt-sessions-pythons-and-keywords>`.
* ``nox.options.tags`` is equivalent to specifying :ref:`-t or --tags <opt-sessions-pythons-and-keywords>`.
* ``nox.options.default_venv_backend`` is equivalent to specifying :ref:`-db or --default-venv-backend <opt-default-venv-backend>`.
* ``nox.options.force_venv_backend`` is equivalent to specifying :ref:`-fb or --force-venv-backend <opt-force-venv-backend>`.
* ``nox.options.reuse_venv`` is equivalent to specifying :ref:`--reuse-venv <opt-reuse-venv>`. Preferred over using ``nox.options.reuse_existing_virtualenvs``.
* ``nox.options.reuse_existing_virtualenvs`` is equivalent to specifying :ref:`--reuse-existing-virtualenvs <opt-reuse-existing-virtualenvs>`. You can force this off by specifying ``--no-reuse-existing-virtualenvs`` during invocation. Alias of ``nox.options.reuse_venv=yes|no``.
* ``nox.options.stop_on_first_error`` is equivalent to specifying :ref:`--stop-on-first-error <opt-stop-on-first-error>`. You can force this off by specifying ``--no-stop-on-first-error`` during invocation.
* ``nox.options.error_on_missing_interpreters`` is equivalent to specifying :ref:`--error-on-missing-interpreters <opt-error-on-missing-interpreters>`. You can force this off by specifying ``--no-error-on-missing-interpreters`` during invocation.
* ``nox.options.error_on_external_run`` is equivalent to specifying :ref:`--error-on-external-run <opt-error-on-external-run>`. You can force this off by specifying ``--no-error-on-external-run`` during invocation.
* ``nox.options.download_python`` is equivalent to specifying ``--download-python``.
* ``nox.options.report`` is equivalent to specifying :ref:`--report <opt-report>`.
* ``nox.options.verbose`` is equivalent to specifying :ref:`-v or --verbose <opt-verbose>`. You can force this off by specifying ``--no-verbose`` during invocation.


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
