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


.. Note:: These docs are for a pre-release version of Nox, so you'll need to use ``pip install --pre nox-automation`` for now~


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

Projects that use Nox
---------------------

Nox is lucky to have several wonderful projects that use it and provide feedback and contributions.

- `Bezier <https://github.com/dhermes/bezier>`__
- `Zazo <https://github.com/pradyunsg/zazo>`__
- `packaging.python.org <https://github.com/pypa/python-packaging-user-guide/>`__
- `google-cloud-python <https://github.com/googlecloudplatform/google-cloud-python>`__
- `gapic-generator-python <https://github.com/googleapis/gapic-generator-python>`__
- `google-resumable-media-python <https://github.com/GoogleCloudPlatform/google-resumable-media-python>`__
- `Google Assistant SDK <https://github.com/googlesamples/assistant-sdk-python>`__
- `OpenCensus Pyhon <https://github.com/census-instrumentation/opencensus-python>`__
- `Subpar <https://github.com/google/subpar>`__

.. _tox: https://tox.readthedocs.org
.. _pip: https://pip.readthedocs.org
.. _py.test: http://pytest.org
.. _virtualenv: https://virtualenv.readthedocs.org
