Tutorial
========

This tutorial will walk you through installing, configuring, and running Nox.


Installation
------------

Nox can be easily installed via `pip`_:

.. code-block:: console

    pip install --upgrade nox

Usually you install this globally, similar to ``tox``, ``pip``, and other similar tools.

If you're interested in running ``nox`` within docker, you can use the `thekevjames/nox images`_ on DockerHub which contain builds for all ``nox`` versions and all supported ``python`` versions.

Running Nox
-----------

The simplest way of running Nox will run all sessions defined in `noxfile.py`:

.. code-block:: console

    nox

However, if you wish to run a single session or subset of sessions you can use the ``-s`` or ``--sessions`` argument:

.. code-block:: console

    nox --sessions lint tests-2.7
    nox -s lint

You can read more about invoking Nox in :doc:`usage`.


Creating a noxfile
------------------

When you run ``nox``, it looks for a file named `noxfile.py` in the current directory. This file contains all of the session definitions. A *session* is an environment and a set of commands to run in that environment. Sessions are analogous to *environments* in tox.

Sessions are declared using the ``@nox.session`` decorator::

    @nox.session
    def lint(session):
        session.install('flake8')
        session.run('flake8')

If you run this via ``nox`` you should see output similar to this:

.. code-block:: console

    nox > Running session lint
    nox > virtualenv .nox/lint
    nox > pip install flake8
    nox > flake8
    nox > Session lint successful. :)


Setting up virtualenvs and installing dependencies
--------------------------------------------------

Nox automatically creates a separate `virtualenv`_ for every session. You can choose which Python interpreter to use when declaring the session. When you install dependencies or run commands within a session, they all use the session's virtualenv. Here's an example of a session that uses Python 2.7, installs dependencies in various ways, and runs a command::


    @nox.session(python='2.7')
    def tests(session):
        # Install pytest
        session.install('pytest')
        # Install everything in requirements-dev.txt
        session.install('-r', 'requirements-dev.txt')
        # Install the current package in editable mode.
        session.install('-e', '.')
        # Run pytest. This uses the pytest executable in the virtualenv.
        session.run('pytest')


You can create as many session as you want and sessions can use multiple Python versions, for example::

    @nox.session(python=['2.7', '3.6'])
    def tests(session):
        ...

If you specify multiple Python versions, Nox will create separate sessions for each Python version. If you run ``nox --list``, you'll see that this generates the following set of sessions:

.. code-block:: console

    * tests-2.7
    * tests-3.6

You can read more about configuring sessions in :doc:`config`.


Running commands
----------------

Running a command in a session is easy - just pass the command name and arguments to :func:`session.run`::

    @nox.session
    def tests(session):
        session.install('pytest')
        session.run('pytest', '-k', 'not slow')

There are some other helpful methods on :class:`nox.sessions.Session`. For example, to change the current working directory you can use :func:`session.chdir`::

    session.chdir('docs')
    session.run('sphinx-build', 'html')


Passing arguments into sessions
-------------------------------

Often it's useful to pass arguments into your test session. Here's a quick example that demonstrates how to use arguments to run tests against a particular file::

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

Session arguments can be parametrized with the :func:`nox.parametrize` decorator. Here's a typical example of parametrizing the Django version to install::

    @nox.session
    @nox.parametrize('django', ['1.9', '2.0'])
    def tests(session, django):
        session.install(f'django=={django}')
        session.run('pytest')

When you run ``nox``, it will create a two distinct sessions:

.. code-block:: console

    $ nox
    nox > Running session tests(django='1.9')
    nox > pip install django==1.9
    ...
    nox > Running session tests(djano='2.0')
    nox > pip install django==2.0


:func:`nox.parametrize` has an interface and usage intentionally similar to `pytest's parametrize <https://pytest.org/latest/parametrize.html#_pytest.python.Metafunc.parametrize>`_.

.. autofunction:: nox.parametrize

You can also stack the decorator to produce sessions that are a combination of the arguments, for example::

    @nox.session
    @nox.parametrize('django', ['1.9', '2.0'])
    @nox.parametrize('database', ['postgres', 'mysql'])
    def tests(session, django, database):
        ...


If you run ``nox --list``, you'll see that this generates the following set of sessions:

.. code-block:: console

    * tests(django='1.9', database='postgres')
    * tests(django='2.0', database='mysql')
    * tests(django='1.9', database='postgres')
    * tests(django='2.0', database='mysql')


If you only want to run one of the parametrized sessions, see :ref:`running_paramed_sessions`.

Giving friendly names to parametrized sessions
----------------------------------------------

The automatically generated names for parametrized sessions, such as ``tests(django='1.9', database='postgres')``, can be long and unwieldy to work with even with using :ref:`keyword filtering <opt-sessions-and-keywords>`. You can give parametrized sessions custom IDs to help in this scenario. These two examples are equivalent:

::

    @nox.session
    @nox.parametrize('django',
        ['1.9', '2.0'],
        ids=['old', 'new'])
    def tests(session, django):
        ...

::

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

::

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


.. _pip: https://pip.readthedocs.org
.. _flake8: https://flake8.readthedocs.org
.. _thekevjames/nox images: https://hub.docker.com/r/thekevjames/nox
.. _virtualenv: https://virtualenv.readthedocs.org
