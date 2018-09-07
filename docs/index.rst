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

    pip install --user --upgrade nox


Nox is configured via a ``noxfile.py`` file in your project's directory. Here's a simple noxfile that runs lint and some tests::

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
- `OpenCensus Python <https://github.com/census-instrumentation/opencensus-python>`__
- `Subpar <https://github.com/google/subpar>`__

.. _tox: https://tox.readthedocs.org
.. _pip: https://pip.readthedocs.org
.. _py.test: http://pytest.org
.. _virtualenv: https://virtualenv.readthedocs.org


Contributors
------------

Nox is free & open-source software and is made possible by community contributors.

* `Thea Flowers <https://github.com/theacodes>`__
* `Luke Sneeringer <https://github.com/lukesneeringer>`__
* `Danny Hermes <https://github.com/dhermes>`__
* `Santos Gallegos <https://github.com/stsewd>`__
* & `more! <https://github.com/theacodes/nox/graphs/contributors>`__

If you'd like to get involved, see :doc:`contrib`.
