Welcome to Nox
==============

.. toctree::
   :hidden:
   :maxdepth: 2

   tutorial
   config
   usage
   cookbook
   CONTRIBUTING
   CHANGELOG

``nox`` is a command-line tool that automates testing in multiple Python environments, similar to `tox`_. Unlike tox, Nox uses a standard Python file for configuration.

Install nox via `pip`_::

    pip install --user --upgrade nox


Nox is configured via a ``noxfile.py`` file in your project's directory. Here's a simple noxfile that runs lint and some tests::

    import nox

    @nox.session
    def tests(session):
        session.install('pytest')
        session.run('pytest')

    @nox.session
    def lint(session):
        session.install('flake8')
        session.run('flake8', '--import-order-style', 'google')

To run both of these sessions, just run::

    nox

For each session, Nox will automatically create a `virtualenv`_ with the appropriate interpreter, install the specified dependencies, and run the commands in order.

To learn how to install and use Nox, see the :doc:`tutorial`. For documentation on configuring sessions, see :doc:`config`. For documentation on running ``nox``, see :doc:`usage`.

.. _tox: https://tox.readthedocs.org
.. _pip: https://pip.readthedocs.org
.. _pytest: http://pytest.org
.. _virtualenv: https://virtualenv.readthedocs.org

Projects that use Nox
---------------------

Nox is lucky to have several wonderful projects that use it and provide feedback and contributions.

- `Bézier <https://github.com/dhermes/bezier>`__
- `cibuildwheel <https://github.com/pypa/cibuildwheel>`__
- `gapic-generator-python <https://github.com/googleapis/gapic-generator-python>`__
- `gdbgui <https://github.com/cs01/gdbgui>`__
- `Google Assistant SDK <https://github.com/googlesamples/assistant-sdk-python>`__
- `google-cloud-python <https://github.com/googlecloudplatform/google-cloud-python>`__
- `google-resumable-media-python <https://github.com/GoogleCloudPlatform/google-resumable-media-python>`__
- `Hydra <https://hydra.cc>`__
- `manylinux <https://github.com/pypa/manylinux>`__
- `OmegaConf <https://github.com/omry/omegaconf>`__
- `OpenCensus Python <https://github.com/census-instrumentation/opencensus-python>`__
- `packaging <https://github.com/pypa/packaging>`__
- `packaging.python.org <https://github.com/pypa/python-packaging-user-guide>`__
- `pip <https://github.com/pypa/pip>`__
- `pipx <https://github.com/pypa/pipx>`__
- `Salt <https://github.com/saltstack/salt>`__
- `Scikit-build <https://github.com/scikit-build/scikit-build>`__
- `Scikit-HEP <https://scikit-hep.org/developer/tasks>`__
- `Subpar <https://github.com/google/subpar>`__
- `Urllib3 <https://github.com/urllib3/urllib3>`__
- `Zazo <https://github.com/pradyunsg/zazo>`__

Other useful projects
---------------------

Nox is not the only tool of its kind. If Nox doesn't quite fit your needs or you want to do more research, we recommend looking at these tools:

- `tox <https://tox.readthedocs.org>`__ is the de-facto standard for managing multiple Python test environments, and is the direct spiritual ancestor to Nox.
- `Invoke <https://www.pyinvoke.org/>`__ is a general-purpose task execution library, similar to Make. Nox can be thought of as if Invoke were tailored specifically to Python testing, so Invoke is a great choice for scripts that need to encompass far more than Nox's specialization.


Maintainers & contributors
--------------------------

Nox is free & open-source software and is made possible by community maintainers and contributors.

Our maintainers are (in alphabetical order):

* `Chris Wilcox <https://github.com/crwilcox>`__
* `Claudio Jolowicz <https://github.com/cjolowicz>`__
* `Danny Hermes <https://github.com/dhermes>`__
* `Diego Ramirez <https://github.com/DiddiLeija>`__
* `Luke Sneeringer <https://github.com/lukesneeringer>`__
* `Santos Gallegos <https://github.com/stsewd>`__
* `Thea Flowers <https://github.com/theacodes>`__
* `Tom Fleet <https://github.com/followtheprocess>`__

Nox also exists due to the various patches and work contributed by `the community <https://github.com/wntrblm/nox/graphs/contributors>`__. If you'd like to get involved, see :doc:`CONTRIBUTING`. We pay our contributors using `Open Collective <https://opencollective.com/python-nox>`__.
