Welcome to Nox
==============

.. toctree::
   :hidden:
   :maxdepth: 2

   tutorial
   config
   usage
   contrib

``nox`` is a command-line tool that automates testing in multiple Python environments, similar to `tox`_. Unlike tox, Nox uses a standard Python file for configuration.

Install nox via `pip`_::

    pip install --upgrade nox-automation

Nox is configured via a ``nox.py`` file in your project's directory. Here's a simple noxfile that runs lint and some tests::

    import nox

    @nox.session
    def tests(session):
        session.install('py.test')
        session.run('py.test')

    @nox.session
    def lint(session):
        session.install('flake8')
        session.run('flake8', '--import-order-style', 'google')

To run both of these sessions, just run::

    nox

For each session, Nox will automatically create `virtualenv`_ with the appropriate interpreter, install the specified dependencies, and run the commands in order.

To learn how to install and use Nox, see the :doc:`tutorial`. For documentation on configuring sessions, see :doc:`config`. For documentation on running ``nox``, see :doc:`usage`.

.. _tox: https://tox.readthedocs.org
.. _pip: https://pip.readthedocs.org
.. _py.test: http://pytest.org
.. _virtualenv: https://virtualenv.readthedocs.org
