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

The ``--list`` command shows the first line of the docstring as the session's description. You can also
show the full docstring of a session using the ``--usage`` option, especially if it has multiple lines.
For example:

.. code-block:: console

    $ nox --usage tests
    Run the test suite.

    The test suite consists of all tests in tests/.


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

    Interpreters are located with the `python-discovery`_ library, which searches
    ``PATH``, version managers (pyenv, mise, asdf, uv), and, on Windows, the
    registry (`PEP 514`_) and the Python `Launcher`_. If a given test needs to use
    the 32-bit version of a given Python on Windows, then ``X.Y-32`` should be used
    as the version.

    .. _Launcher: https://docs.python.org/3/using/windows.html#python-launcher-for-windows
    .. _python-discovery: https://pypi.org/project/python-discovery/
    .. _PEP 514: https://peps.python.org/pep-0514/

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

A free-threaded build can be requested with the ``t`` suffix, e.g. ``python='3.13t'``.

You can also give a `PEP 440`_ version specifier instead of an exact version, and
Nox will use the first installed interpreter that satisfies it:

.. code-block:: python

    @nox.session(python='>=3.14')
    def tests(session):
        pass

    @nox.session(python='>=3.11,<3.13')
    def lint(session):
        pass

.. note::

    Range specifiers are only supported on the ``venv``, ``virtualenv``, and ``uv``
    backends, not on conda backends.

If the specified python interpreter is not found, Nox can automatically download it when ``--download-python`` is set to ``auto`` (the default) or ``always``. ``never`` avoids the download. This requires the ``[pbs]`` extra when not using uv as a backend. When a range is given, the floor of its lowest bound is downloaded (``>=3.14`` downloads ``3.14``); a range with no lower bound (such as ``<3.14``) cannot be downloaded.

When collecting your sessions, Nox will create a separate session for each interpreter. You can see these sessions when running ``nox --list``. For example this Noxfile:

.. code-block:: python

    @nox.session(python=['3.10', '3.11', '3.12', '3.13', '3.14'])
    def tests(session):
        pass

Will produce these sessions:

.. code-block:: console

    * tests-3.10
    * tests-3.11
    * tests-3.12
    * tests-3.13
    * tests-3.14

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

.. tip::

    If a session targets an end-of-life Python version while Nox itself runs on
    a newer Python, prefer the ``venv`` backend for that session. The
    ``virtualenv`` backend runs from Nox's interpreter and may no longer support
    bootstrapping older target interpreters after they reach end of life, which
    can seed incompatible packages into the session environment. The ``venv``
    backend uses the target interpreter's standard library ``venv`` module
    instead.

    .. code-block:: python

        @nox.session(python='3.7', venv_backend='venv')
        def tests(session):
            pass

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


.. _environments:

Environments and tasks
----------------------

A session is really two things: an *environment* (a virtualenv and the
packages installed into it) and a *task* (the thing you want to do, like
running pytest). ``@nox.session`` fuses the two under one name; you can also
declare them separately so several tasks share one environment:

.. code-block:: python

    import nox

    tooling = nox.env(
        "tooling",
        python="3.12",
        dependencies=["prek", "mypy"],
    )

    @tooling.task
    def lint(session):
        """Run the linters."""
        session.run("prek", "run", "--all-files", *session.posargs)

    @tooling.task(tags=["check"], default=False)
    def typecheck(session):
        session.run("mypy", "src")

Each task is a session named ``environment:task`` — here ``tooling:lint``
and ``tooling:typecheck`` — and all of an environment's tasks run in one
shared virtualenv, created and provisioned once per invocation. A classic
``@nox.session`` is exactly an environment and a task sharing one name, so
``nox -s tests`` and ``requires=["tests"]`` keep working unchanged.

Environment names (and aliases, below) are globally unique and share a
namespace with classic session names; task names only need to be unique
within their environment. On the command line and in ``requires``, you can
refer to a task by its full ``env:task`` id, by its bare task name if that's
unambiguous across environments, or by the environment name to select the
environment's default tasks. See :doc:`usage` for details. Because session
names share this grammar, new session names containing ``:`` or parentheses
are deprecated (existing ones keep working with a warning).

``nox.env()`` accepts the environment-level options of ``@nox.session`` —
``python``, ``venv_backend``, ``venv_params``, ``reuse_venv``,
``download_python``, and ``tags`` (tags are inherited by the environment's
tasks) — plus the provisioning options below. Listing multiple Pythons
creates one environment instance per interpreter: ``tests-3.11:run``,
``tests-3.12:run``, and so on. ``@nox.parametrize`` works on tasks, but
``python`` must be set on the environment, not parametrized on a task.

Declarative dependencies and staleness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unlike classic sessions, declarative environments record their provisioning
inputs in a stamp file (``.nox-env.json``) inside the environment. On the
next run the environment is reused, and if the stamp still matches — same
dependency list, same lock file contents, same backend and Python — the
installation step is skipped entirely, making repeat runs fast by default.
If the inputs changed, lock file environments are re-synced in place (their
syncs are exact), while a plain ``dependencies`` list recreates the
environment, so removed dependencies actually disappear.
``--reuse-venv=never`` forces full recreation, and ``-R``/``--no-install``
skip installs as usual.

For install-time logic that can't be expressed declaratively, add a setup
hook. It runs after the declared dependencies are installed, and only when
the environment is created or stale:

.. code-block:: python

    @tooling.setup
    def _(session):
        if sys.platform == "linux":
            session.install("pyenchant")

Since Nox cannot see when a hook's *effect* changes, an environment with a
setup hook is re-synced on every run unless you pass a ``setup_stamp``
string to ``nox.env()`` and bump it whenever the hook's behavior changes.

Using ``session.install()`` inside a task still works, but for environments
with more than one task it warns, since run-time installs into a shared
environment are invisible to the staleness check.

Lock files
~~~~~~~~~~

Specialized environment types install from lock files instead of a
dependency list:

.. code-block:: python

    # PEP 751 pylock file, installed exactly with `uv pip sync`:
    ci = nox.env.pylock("ci", lockfile="pylock.toml")

    # A uv project's uv.lock, synced with `uv sync --locked`
    # (requires the "uv" backend, which is the default here):
    dev = nox.env.uv("dev", groups=["dev"], location=".venv")

``nox.env.uv()`` accepts ``lockfile`` (default ``uv.lock``; the project is
the lock file's directory), ``groups``, ``extras``, ``all_extras``,
``no_default_groups``, ``no_install_project``, and ``sync_args`` for
anything else. It requires the ``uv`` backend and refuses to sync under
``--force-venv-backend``/``--no-venv``, since ``uv sync`` would otherwise
target the project's own ``.venv``. The lock file's contents are part of
the environment stamp, so editing the lock triggers a re-sync on the next
run.

Other formats can be supported by subclassing :class:`nox.Environment` and
overriding ``stamp_data()`` (return the content hashes of your inputs, or
``None`` to always re-sync) and ``sync(session)`` (run the install
commands). Instantiating the subclass registers it, so a package like a
poetry integration can simply ship its own environment type.

Environment location
~~~~~~~~~~~~~~~~~~~~

By default environments live under ``--envdir`` (``.nox``). Pass
``location=`` to place one somewhere specific — for example ``.venv``, so
your editor and Nox share an environment:

.. code-block:: python

    dev = nox.env.uv("dev", location=".venv")

The path is relative to the noxfile's directory. Environments with multiple
Pythons must include a ``{name}`` or ``{python}`` placeholder (e.g.
``location=".venvs/{name}"``) — two selected environment instances may
never resolve to the same location. Nox will adopt an existing virtualenv
at the location, but refuses to touch a non-empty directory that isn't one,
and never writes ``.gitignore`` or ``CACHEDIR.TAG`` outside ``--envdir``.

Aliases
~~~~~~~

An alias gives a globally unique name to one or more sessions and can be
used anywhere a session name can — on the command line, in ``requires``, or
in ``nox.options.sessions``:

.. code-block:: python

    nox.alias("check", "tooling:lint", "tooling:typecheck")
    nox.alias("style", "tooling:lint")

Aliases are expanded recursively at selection time (a cycle is an error)
and don't appear as sessions themselves. An alias that shadows an existing
task name takes precedence, with a warning.

Environment API reference
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: nox.Environment
    :members:

.. autofunction:: nox.alias


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
