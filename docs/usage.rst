Command-line usage
==================

Invocation
----------

Nox is normally invoked on the command line:

.. code-block:: console

    nox


You can also invoke Nox via the Python interpreter:

.. code-block:: console

    python3 -m nox


Listing available sessions
--------------------------

To list all available sessions, including parametrized sessions:


.. code-block:: console

    nox -l
    nox --list
    nox --list-sessions

If you'd like to use the output in later processing, you can add ``--json`` to
get json output for the selected session. Fields include ``session`` (pretty
name), ``name``, ``description``, ``python`` (null if not specified), ``tags``,
and ``call_spec`` (for parametrized sessions).


.. _session_execution_order:

Running all sessions
--------------------

You can run every session by just executing ``nox`` without any arguments:

.. code-block:: console

    nox

The order that sessions are executed is the order that they appear in the Noxfile.


.. _opt-sessions-pythons-and-keywords:

Specifying one or more sessions
-------------------------------

By default Nox will run all sessions defined in the Noxfile. However, you can choose to run a particular set of them using ``--session``, ``-s``, or ``-e``:

.. tabs::

   .. code-tab:: console CLI options

         nox --session tests
         nox -s lint tests
         nox -e lint

   .. code-tab:: console Environment variables

         NOXSESSION=tests nox
         NOXSESSION=lint nox
         NOXSESSION=lint,tests nox

Nox will run these sessions in the same order they are specified.

If you have a :ref:`configured session's virtualenv <virtualenv config>`, you can choose to run only sessions with given Python versions:

.. tabs::

   .. code-tab:: console CLI options

         nox --python 3.12
         nox -p 3.11 3.12

   .. code-tab:: console Environment variables

         NOXPYTHON=3.12 nox
         NOXPYTHON=3.11,3.12 nox

You can also use `pytest-style keywords`_ using ``-k`` or ``--keywords``, and
tags using ``-t`` or ``--tags`` to filter test sessions:

.. code-block:: console

    nox -k "not lint"
    nox -k "tests and not lint"
    nox -k "not my_tag"
    nox -t "my_tag" "my_other_tag"

.. _pytest-style keywords: https://docs.pytest.org/en/latest/usage.html#specifying-tests-selecting-tests


.. _running_paramed_sessions:

Specifying parametrized sessions
--------------------------------

If you have a :ref:`parametrized <parametrized>` session such as:

.. code-block:: python

    @nox.parametrize('django', ['1.9', '2.0'])
    def tests(session, django):
        ...

Then running ``nox --session tests`` will actually run all parametrized versions of the session. If you want the run the session with a particular set of parametrized arguments, you can specify them with the session name:

.. code-block:: console

    nox --session "tests(django='1.9')"
    nox --session "tests(django='2.0')"


.. _opt-default-venv-backend:

Changing the sessions default backend
-------------------------------------

By default Nox uses ``virtualenv`` as the virtual environment backend for the sessions, but it also supports ``uv``, ``conda``, ``mamba``, ``micromamba``, and ``venv`` as well as no backend (passthrough to whatever python environment Nox is running on). You can change the default behaviour by using ``-db <backend>`` or ``--default-venv-backend <backend>``. Supported names are ``('none', 'uv', 'virtualenv', 'conda', 'mamba', 'venv')``.


.. tabs::

   .. code-tab:: console CLI options

         nox -db conda
         nox --default-venv-backend conda

   .. code-tab:: console Environment variables

         NOX_DEFAULT_VENV_BACKEND=conda

.. note::

   The ``uv``, ``conda``, ``mamba``, and ``micromamba`` backends require their
   respective programs be pre-installed. ``uv`` is distributed as a Python
   package and can be installed with the ``nox[uv]`` extra.

You can also set this option with the ``NOX_DEFAULT_VENV_BACKEND`` environment variable, or in the Noxfile with ``nox.options.default_venv_backend``. In case more than one is provided, the command line argument overrides the environment variable, which in turn overrides the Noxfile configuration.

Note that using this option does not change the backend for sessions where ``venv_backend`` is explicitly set.

.. warning::

   The ``uv`` backend does not install anything by default, including ``pip``,
   as ``uv pip`` is used to install programs instead. If you need to manually
   interact with pip, you should install it with ``session.install("pip")``.

Backends that could be missing (``uv``, ``conda``, ``mamba``, and ``micromamba``) can have a fallback using ``|``, such as ``uv|virtualenv`` or ``micromamba|mamba|conda``. This will use the first item that is available on the users system.

If you need to check to see which backend was selected, you can access it via
``session.venv_backend`` in your noxfile.

.. _opt-force-venv-backend:

Forcing the sessions backend
----------------------------

You might work in a different environment than a project's default continuous integration settings, and might wish to get a quick way to execute the same tasks but on a different venv backend. For this purpose, you can temporarily force the backend used by **all** sessions in the current Nox execution by using ``-fb <backend>`` or ``--force-venv-backend <backend>``. No exceptions are made, the backend will be forced for all sessions run whatever the other options values and Noxfile configuration. Supported names are ``('none', 'uv', 'virtualenv', 'conda', 'mamba', 'micromamba', 'venv')``.

.. code-block:: console

    nox -fb conda
    nox --force-venv-backend conda


You can also set this option in the Noxfile with ``nox.options.force_venv_backend``. In case both are provided, the commandline argument takes precedence.

Finally note that the ``--no-venv`` flag is a shortcut for ``--force-venv-backend none`` and allows to temporarily run all selected sessions on the current python interpreter (the one running Nox).

.. code-block:: console

    nox --no-venv

.. _opt-reuse-existing-virtualenvs:
.. _opt-reuse-venv:

Re-using virtualenvs
--------------------

By default, Nox deletes and recreates virtualenvs every time it is run. This is
usually fine for most projects and continuous integration environments as
`pip's caching <https://pip.pypa.io/en/stable/cli/pip_install/#caching>`_ makes
re-install rather quick.  However, there are some situations where it is
advantageous to reuse the virtualenvs between runs.  Use ``-r`` or
``--reuse-existing-virtualenvs`` or for fine-grained control use
``--reuse-venv=yes|no|always|never``:

.. code-block:: console

    nox -r
    nox --reuse-existing-virtualenvs
    nox --reuse-venv=yes # preferred

If the Noxfile sets ``nox.options.reuse_existing_virtualenvs``, you can override the Noxfile setting from the command line by using ``--no-reuse-existing-virtualenvs``.
Similarly you can override ``nox.options.reuse_venvs`` from the Noxfile via the command line by using ``--reuse-venv=yes|no|always|never``.

.. note::

    ``--reuse-existing-virtualenvs`` is a alias for ``--reuse-venv=yes`` and ``--no-reuse-existing-virtualenvs`` is an alias for ``--reuse-venv=no``.

Additionally, you can skip the re-installation of packages when a virtualenv is reused.
Use ``-R`` or ``--reuse-existing-virtualenvs --no-install`` or ``--reuse-venv=yes --no-install``:

.. code-block:: console

    nox -R
    nox --reuse-existing-virtualenvs --no-install
    nox --reuse-venv=yes --no-install

The ``--no-install`` option causes the following session methods to return early:

- :func:`session.install <nox.sessions.Session.install>`
- :func:`session.conda_install <nox.sessions.Session.conda_install>`
- :func:`session.run_install <nox.sessions.Session.run_install>`

The ``never`` and ``always`` options in ``--reuse-venv`` gives you more fine-grained control
as it ignores when a ``@nox.session`` has ``reuse_venv=True|False`` defined.

These options have no effect if the virtualenv is not being reused.

.. _opt-running-extra-pythons:

Running additional Python versions
----------------------------------

In addition to Nox supporting executing single sessions, it also supports running Python versions that aren't specified using ``--extra-pythons``.

.. tabs::

   .. code-tab:: console CLI options

         nox --extra-pythons 3.8 3.9 3.10

   .. code-tab:: console Environment variables

         NOXEXTRAPYTHON=3.8,3.9,3.10 nox


This will, in addition to specified Python versions in the Noxfile, also create sessions for the specified versions.

This option can be combined with ``--python`` to replace, instead of appending, the Python interpreter for a given session:

.. tabs::

   .. code-tab:: console CLI options

         nox --python 3.11 --extra-python 3.11 -s lint

   .. code-tab:: console Environment variables

         NOXPYTHON=3.11 NOXEXTRAPYTHON=3.11 NOXSESSION=lint nox

Instead of passing both options, you can use the ``--force-python`` shorthand:

.. tabs::

   .. code-tab:: console CLI options

         nox --force-python 3.11 -s lint

   .. code-tab:: console Environment variables

         NOXFORCEPYTHON=3.11 NOXSESSION=lint nox

Also, you can specify ``python`` in place of a specific version. This will run the session
using the ``python`` specified for the current ``PATH``:

.. tabs::

   .. code-tab:: console CLI options

         nox --force-python python -s lint

   .. code-tab:: console Environment variables

         NOXFORCEPYTHON=python NOXSESSION=lint nox

.. _opt-stop-on-first-error:

Stopping if any session fails
-----------------------------

By default Nox will continue to run all sessions even if one fails. You can use ``--stop-on-first-error`` to make Nox abort as soon as the first session fails::

    nox --stop-on-first-error

If the Noxfile sets ``nox.options.stop_on_first_error``, you can override the Noxfile setting from the command line by using ``--no-stop-on-first-error``.


.. _opt-error-on-missing-interpreters:

Failing sessions when the interpreter is missing
------------------------------------------------

By default, when not on CI, Nox will skip sessions where the Python interpreter can't be found. If you want Nox to mark these sessions as failed, you can use ``--error-on-missing-interpreters``:

.. code-block:: console

    nox --error-on-missing-interpreters

If the Noxfile sets ``nox.options.error_on_missing_interpreters``, you can override the Noxfile setting from the command line by using ``--no-error-on-missing-interpreters``.

If being run on Continuous Integration (CI) systems, Nox will treat missing interpreters as errors by default to avoid sessions silently passing when the requested python interpreter is not installed. Nox does this by looking for an environment variable called ``CI`` which is a convention used by most CI providers.

.. _opt-error-on-external-run:

Disallowing external programs
-----------------------------

By default Nox will warn but ultimately allow you to run programs not installed in the session's virtualenv. You can use ``--error-on-external-run`` to make Nox fail the session if it uses any external program without explicitly passing ``external=True`` into :func:`session.run <nox.session.Session.run>`:

.. code-block:: console

    nox --error-on-external-run

If the Noxfile sets ``nox.options.error_on_external_run``, you can override the Noxfile setting from the command line by using ``--no-error-on-external-run``.

Specifying a different configuration file
-----------------------------------------

If for some reason your Noxfile is not named *noxfile.py*, you can use ``--noxfile`` or ``-f``:

.. code-block:: console

    nox --noxfile something.py
    nox -f something.py


.. _opt-envdir:

Storing virtualenvs in a different directory
--------------------------------------------

By default Nox stores virtualenvs in ``./.nox``, however, you can change this using ``--envdir``:

.. code-block:: console

    nox --envdir /tmp/envs


Skipping everything but install commands
----------------------------------------

There are a couple of cases where it makes sense to have Nox only run ``install`` commands, such as preparing an environment for offline testing or re-creating the same virtualenvs used for testing. You can use ``--install-only`` to skip ``run`` commands.

For example, given this Noxfile:

.. code-block:: python

    @nox.session
    def tests(session):
        session.install("pytest")
        session.install(".")
        session.run("pytest")


Running:

.. code-block:: console

    nox --install-only


Would run both ``install`` commands, but skip the ``run`` command:

.. code-block:: console

    nox > Running session tests
    nox > Creating virtualenv using python3.12 in ./.nox/tests
    nox > python -m pip install pytest
    nox > python -m pip install .
    nox > Skipping pytest run, as --install-only is set.
    nox > Session tests was successful.


Forcing non-interactive behavior
--------------------------------

:attr:`session.interactive <nox.sessions.Session.interactive>` can be used to tell if Nox is being run from an interactive terminal (such as an actual human running it on their computer) vs run in a non-interactive terminal (such as a continuous integration system).

.. code-block:: python

    @nox.session
    def docs(session):
        ...

        if session.interactive:
            nox.run("sphinx-autobuild", ...)
        else:
            nox.run("sphinx-build", ...)

Sometimes it's useful to force Nox to see the session as non-interactive. You can use the ``--non-interactive`` argument to do this:

.. code-block:: bash

    nox --non-interactive


This will cause ``session.interactive`` to always return ``False``.


Controlling color output
------------------------

By default, Nox will output colorful logs if you're using in an interactive
terminal. However, if you are redirecting ``stderr`` to a file or otherwise
not using an interactive terminal, or the environment variable ``NO_COLOR`` is
set, Nox will output in plaintext. If this is not set, and ``FORCE_COLOR`` is
present, color will be forced.

You can manually control Nox's output using the ``--nocolor`` and ``--forcecolor`` flags.

For example, this will always output colorful logs:

.. code-block:: console

    nox --forcecolor

However, this will never output colorful logs:

.. code-block:: console

    nox --nocolor


.. _opt-verbose:


Controlling commands verbosity
------------------------------

By default, Nox will only show output of commands that fail, or, when the commands get passed ``silent=False``.
By either passing ``--verbose`` to Nox or setting ``nox.options.verbose = True``, all output of all commands
run is shown, regardless of the silent argument.


.. _opt-report:


Outputting a machine-readable report
------------------------------------

You can output a report in ``json`` format by specifying ``--report``:

.. code-block:: console

    nox --report status.json


Converting from tox
-------------------

Nox has experimental support for converting ``tox.ini`` files into ``noxfile.py`` files. This doesn't support every feature of tox and is intended to just do most of the mechanical work of converting over- you'll likely still need to make a few changes to the converted ``noxfile.py``.

To use the converter, install ``nox`` with the ``tox_to_nox`` extra:

.. code-block:: console

    pip install --upgrade nox[tox_to_nox]

Then, just run ``tox-to-nox`` in the directory where your ``tox.ini`` resides:

.. code-block:: console

    tox-to-nox

This will create a ``noxfile.py`` based on the environments in your ``tox.ini``. Some things to note:

- `Generative environments`_ work, but will be converted as individual environments. ``tox-to-nox`` isn't quite smart enough to turn these into :ref:`parametrized <running_paramed_sessions>` sessions, but it should be straightforward to manually pull out common configuration for parametrization.
- Due to the way tox parses its configuration, all `substitutions`_ are baked in when converting. This means you'll need to replace the static strings in the ``noxfile.py`` with appropriate variables.
- Several non-common tox options aren't implemented, but it's possible to do so. Please file a feature request if you run into one you think will be useful.

.. _Generative environments: http://tox.readthedocs.io/en/latest/config.html#generating-environments-conditional-settings
.. _substitutions: http://tox.readthedocs.io/en/latest/config.html#substitutions


Shell Completion
----------------
Add the appropriate command to your shell's config file
so that it is run on startup. You will likely have to restart
or re-login for the autocompletion to start working.

bash

.. code-block:: console

    eval "$(register-python-argcomplete nox)"

zsh

.. code-block:: console

    # To activate completions for zsh you need to have
    # bashcompinit enabled in zsh:
    autoload -U bashcompinit
    bashcompinit

    # Afterwards you can enable completion for Nox:
    eval "$(register-python-argcomplete nox)"

tcsh

.. code-block:: console

    eval `register-python-argcomplete --shell tcsh nox`

fish

.. code-block:: console

    register-python-argcomplete --shell fish nox | .
