Tutorial
========

This tutorial will walk you through installing, configuring, and running Nox.


Installation
------------

Nox can be easily installed via `pip`_:

.. code-block:: console

    python3 -m pip install nox

You may want to use the `user site`_ to avoid messing with your global Python install:

.. code-block:: console

    python3 -m pip install --user nox

Or you can be extra fancy and use `pipx`_:

.. code-block:: console

    pipx install nox

Either way, Nox is usually installed *globally*, similar to ``tox``, ``pip``, and other similar tools.

If you're interested in running ``nox`` within `docker`_, you can use the `thekevjames/nox images`_ on DockerHub which contain builds for all ``nox`` versions and all supported ``python`` versions.

If you want to run ``nox`` within `GitHub Actions`_, you can use the `excitedleigh/setup-nox action`_, which installs the latest ``nox`` and makes available all Python versions provided by the GitHub Actions environment.

.. _pip: https://pip.readthedocs.org
.. _user site: https://packaging.python.org/tutorials/installing-packages/#installing-to-the-user-site
.. _pipx: https://packaging.python.org/guides/installing-stand-alone-command-line-tools/
.. _docker: https://www.docker.com/
.. _thekevjames/nox images: https://hub.docker.com/r/thekevjames/nox
.. _GitHub Actions: https://github.com/features/actions
.. _excitedleigh/setup-nox action: https://github.com/marketplace/actions/setup-nox

Writing the configuration file
------------------------------

Nox is configured via a file called ``noxfile.py`` in your project's directory.
This file is a Python file that defines a set of *sessions*. A *session* is
an environment and a set of commands to run in that environment. If you're
familiar with tox sessions are analogous to *environments*. If you're familiar
with GNU Make, sessions are analogous to *targets*.

Sessions are declared using the ``@nox.session`` decorator. This is similar to
how Flask uses ``@app.route``.

Here's a basic Noxfile that runs `flake8`_ against ``example.py`` (you can create
``example.py`` yourself)::

    import nox

    @nox.session
    def lint(session):
        session.install("flake8")
        session.run("flake8", "example.py")

.. _flake8: http://flake8.pycqa.org/en/latest/


Running Nox for the first time
------------------------------

Now that you've installed Nox and have a Noxfile you can run Nox! Open your
project's directory in a terminal and run ``nox``. You should see something
like this:

.. code-block:: console

    $ nox
    nox > Running session lint
    nox > Creating virtualenv using python3.7 in .nox/lint
    nox > pip install flake8
    nox > flake8 example.py
    nox > Session lint was successful.


**✨ You've now successfully used Nox for the first time! ✨**

The rest of this tutorial will take you through other common things you'll
likely want to do with Nox. You can also jump into :doc:`usage` and
:doc:`config` docs if you want.


Installing dependencies
-----------------------

Nox more or less passes ``session.install`` through to ``pip``, so you can
install stuff in the usual way. Here's some examples:

To install one or more packages at a time:

.. code-block:: python

    @nox.session
    def tests(session):
        # same as pip install pytest protobuf>3.0.0
        session.install("pytest", "protobuf>3.0.0")
        ...

To install a ``requirements.txt`` file:

.. code-block:: python

    @nox.session
    def tests(session):
        # same as pip install -r requirements.txt
        session.install("-r", "requirements.txt")
        ...

If your project is a Python package and you want to install it:

.. code-block:: python

    @nox.session
    def tests(session):
        # same as pip install .
        session.install(".")
        ...

In some cases such as Python binary extensions, your package may depend on
code compiled outside of the Python ecosystem. To make sure a low-level
dependency (e.g. ``libfoo``) is available during installation

.. code-block:: python

    @nox.session
    def tests(session):
        ...
        session.run_always(
            "cmake", "-DCMAKE_BUILD_TYPE=Debug",
            "-S", libfoo_src_dir,
            "-B", build_dir,
            external=True,
        )
        session.run_always(
            "cmake",
            "--build", build_dir,
            "--config", "Debug",
            "--target", "install",
            external=True,
        )
        session.install(".")
        ...

Running commands
----------------

The ``session.run`` function lets you run commands within the context of your
session's virtual environment. Here's a few examples:

You can install and run Python tools:

.. code-block:: python

    @nox.session
    def tests(session):
        session.install("pytest")
        session.run("pytest")


If you want to pass more arguments to a program just add more arguments to ``run``:

.. code-block:: python

    @nox.session
    def tests(session):
        session.install("pytest")
        session.run("pytest", "-v", "tests")


You can also pass environment variables:

.. code-block:: python

    @nox.session
    def tests(session):
        session.install("black")
        session.run(
            "pytest",
            env={
                "FLASK_DEBUG": "1"
            }
        )

See :func:`nox.sessions.Session.run` for more options and examples for running
programs.


Selecting which sessions to run
-------------------------------

Once you have multiple sessions in your Noxfile you'll notice that Nox will
run them all by default. While this is useful, it often useful to just run
one or two at a time. You can use the ``--sessions`` argument (or ``-s``) to
select which sessions to run. You can use the ``--list`` argument to show which
sessions are available and which will be run. Here's some examples:

Here's a Noxfile with three sessions:

.. code-block:: python

    import nox

    @nox.session
    def test(session):
        ...

    @nox.session
    def lint(session):
        ...

    @nox.session
    def docs(session):
        ...


If you just run ``nox --list`` you'll see that all sessions are selected:

.. code-block:: console

    Sessions defined in noxfile.py:

    * test
    * lint
    * docs

    sessions marked with * are selected,
    sessions marked with - are skipped.


If you run ``nox --list --sessions lint`` you'll see that only the lint session
is selected:

.. code-block:: console

    Sessions defined in noxfile.py:

    - test
    * lint
    - docs

    sessions marked with * are selected,
    sessions marked with - are skipped.


And if you run ``nox --sessions lint`` Nox will just run the lint session:

.. code-block:: console

    nox > Running session lint
    nox > Creating virtualenv using python3 in .nox/lint
    nox > ...
    nox > Session lint was successful.

There are many more ways to select and run sessions! You can read more about
invoking Nox in :doc:`usage`.


Testing against different and multiple Pythons
----------------------------------------------

Many projects need to support either a specific version of Python or multiple
Python versions. You can have Nox run your session against multiple
interpreters by specifying ``python`` to ``@nox.session``. Here's some examples:

If you want your session to specifically run against a single version of Python only:

.. code-block:: python

    @nox.session(python="3.7")
    def test(session):
        ...

If you want your session to run against multiple versions of Python:

.. code-block:: python

    @nox.session(python=["2.7", "3.6", "3.7"])
    def test(session):
        ...

You'll notice that running ``nox --list`` will show that this one session has
been expanded into three distinct sessions:

.. code-block:: console

    Sessions defined in noxfile.py:

    * test-2.7
    * test-3.6
    * test-3.7

You can run all of the ``test`` sessions using ``nox --sessions test`` or run
an individual one using the full name as displayed in the list, for example,
``nox --sessions test-3.5``. More details on selecting sessions can be found
over in the :doc:`usage` documentation.

You can read more about configuring the virtual environment used by your
sessions over at :ref:`virtualenv config`.


Testing with conda
------------------

Some projects, especially in the data science community, need to test that
they work in a conda environment. If you want your session to run in a conda
environment:

.. code-block:: python

    @nox.session(venv_backend="conda")
    def test(session):
        ...

Install packages with conda:

.. code-block:: python

    session.conda_install("pytest")

It is possible to install packages with pip into the conda environment, but
it's a best practice only install pip packages with the ``--no-deps`` option.
This prevents pip from breaking the conda environment by installing
incompatible versions of packages already installed with conda.

.. code-block:: python

    session.install("contexter", "--no-deps")
    session.install("-e", ".", "--no-deps")


Parametrization
---------------

Just like Nox can handle running against multiple interpreters, Nox can also
handle running your sessions with a list of different arguments using the
:func:`nox.parametrize` decorator.

Here's a short example of using parametrization to test against two different
versions of Django:

.. code-block:: python

    @nox.session
    @nox.parametrize("django", ["1.9", "2.0"])
    def test(session, django):
        session.install(f"django=={django}")
        session.run("pytest")


If you run ``nox --list`` you'll see that Nox expands your one session into
multiple sessions. One for each argument value that you want to be passed to
your session:

.. code-block:: console

    Sessions defined in noxfile.py:

    * test(django='1.9')
    * test(django='2.0')


:func:`nox.parametrize` has an interface and usage intentionally similar to
`pytest's parametrize`_. It's an extremely powerful feature of Nox. You can
read more about parametrization and see more examples over at
:ref:`parametrized`.

.. _pytest's parametrize: https://pytest.org/latest/parametrize.html#_pytest.python.Metafunc.parametrize


Next steps
----------

Look at you! You're now basically an expert at Nox! ✨

For this point you can:

* Read more docs, such as :doc:`usage` and :doc:`config`.
* Give us feedback or contribute, see :doc:`CONTRIBUTING`.

Have fun! 💜
