Tutorial
========

This tutorial will walk you through installing, configuring, and running Nox.


Installation
------------

Nox can be easily installed via `pip`_::

    pip install --upgrade nox

Usually you install this globally, similar to ``tox``, ``pip``, and other similar tools.


Running Nox
-----------

The simplest way of running Nox will run all sessions defined in `noxfile.py`::

    nox

However, if you wish to run a single session or subset of sessions you can use the ``-s`` argument::

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

If you run this via ``nox`` you should see output similar to this::

    nox > Running session lint
    nox > virtualenv /tmp/example/.nox/lint
    nox > pip install --upgrade flake8
    nox > flake8
    nox > Session lint successful. :)


Setting up virtualenvs and installing dependencies
--------------------------------------------------

Nox automatically creates a separate `virtualenv`_ for every session. You can choose which Python interpreter to use when declaring the session. When you install dependencies or run commands within a session, they all use the session's virtualenv. Here's an example of a session that uses Python 2.7, installs dependencies in various ways, and runs a command::


    @nox.session(python='2.7')
    def tests(session):
        # Install py.test
        session.install('pytest')
        # Install everything in requirements-dev.txt
        session.install('-r', 'requirements-dev.txt')
        # Install the current package in editable mode.
        session.install('-e', '.')
        # Run py.test. This uses the py.test executable in the virtualenv.
        session.run('py.test')


You can create as many session as you want and sessions can use multiple Python versions, for example::

    @nox.session(python=['2.7', '3.6'])
    def tests(session):
        ...

If you specify multiple Python versions, Nox will create separate sessions for each Python version. If you run ``nox --list-sessions``, you'll see that this generates the following set of sessions::

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
        session.install('py.test')

        if session.posargs:
            test_files = session.posargs
        else:
            test_files = ['test_a.py', 'test_b.py']

        session.run('pytest', *test_files)

Now you if you run::

    nox

Then nox will run::

    pytest test_a.py test_b.py

But if you run::

    nox -- test_c.py

Then nox will run::

    pytest test_c.py


.. _parametrized:

Parametrizing sessions
----------------------

Session arguments can be parametrized with the :func:`nox.parametrize` decorator. Here's a typical example of parametrizing the Django version to install::

    @nox.session
    @nox.parametrize('django', ['1.9', '2.0'])
    def tests(session, django):
        session.install(f'django=={django}')
        session.run('py.test')

When you run ``nox``, it will create a two distinct sessions::

    $ nox
    nox > Running session tests(django='1.9')
    nox > pip install --upgrade django==1.9
    ...
    nox > Running session tests(djano='2.0')
    nox > pip install --upgrade django==2.0


:func:`nox.parametrize` has an interface and usage intentionally similar to `py.test's parametrize <https://pytest.org/latest/parametrize.html#_pytest.python.Metafunc.parametrize>`_.

.. autofunction:: nox.parametrize

You can also stack the decorator to produce sessions that are a combination of the arguments, for example::

    @nox.session
    @nox.parametrize('django', ['1.9', '2.0'])
    @nox.parametrize('database', ['postgres', 'mysql'])
    def tests(session, django, database):
        ...


If you run ``nox --list-sessions``, you'll see that this generates the following set of sessions::

    * tests(django='1.9', database='postgres')
    * tests(django='2.0', database='mysql')
    * tests(django='1.9', database='postgres')
    * tests(django='2.0', database='mysql')


If you only want to run one of the parametrized sessions, see :ref:`running_paramed_sessions`.

.. _pip: https://pip.readthedocs.org
.. _flake8: https://flake8.readthedocs.org
.. _virtualenv: https://virtualenv.readthedocs.org
