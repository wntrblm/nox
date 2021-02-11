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

By default Nox will run all sessions defined in the noxfile. However, you can choose to run a particular set of them using ``--session``, ``-s``, or ``-e``:

.. code-block:: console

    nox --session tests
    nox -s lint tests
    nox -e lint

You can also use the ``NOXSESSION`` environment variable:

.. code-block:: console

    NOXSESSION=lint nox
    NOXSESSION=lint,tests nox

Nox will run these sessions in the same order they are specified.

If you have a :ref:`configured session's virtualenv <virtualenv config>`, you can choose to run only sessions with given Python versions:

.. code-block:: console

    nox --python 3.8
    nox -p 3.7 3.8

You can also use `pytest-style keywords`_ to filter test sessions:

.. code-block:: console

    nox -k "not lint"
    nox -k "tests and not lint"

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

By default nox uses ``virtualenv`` as the virtual environment backend for the sessions, but it also supports ``conda`` and ``venv`` as well as no backend (passthrough to whatever python environment nox is running on). You can change the default behaviour by using ``-db <backend>`` or ``--default-venv-backend <backend>``. Supported names are ``('none', 'virtualenv', 'conda', 'venv')``.

.. code-block:: console

    nox -db conda
    nox --default-venv-backend conda


You can also set this option in the Noxfile with ``nox.options.default_venv_backend``. In case both are provided, the commandline argument takes precedence.

Note that using this option does not change the backend for sessions where ``venv_backend`` is explicitly set.


.. _opt-force-venv-backend:

Forcing the sessions backend
----------------------------

You might work in a different environment than a project's default continuous integration setttings, and might wish to get a quick way to execute the same tasks but on a different venv backend. For this purpose, you can temporarily force the backend used by **all** sessions in the current nox execution by using ``-fb <backend>`` or ``--force-venv-backend <backend>``. No exceptions are made, the backend will be forced for all sessions run whatever the other options values and nox file configuration. Supported names are ``('none', 'virtualenv', 'conda', 'venv')``.

.. code-block:: console

    nox -fb conda
    nox --force-venv-backend conda


You can also set this option in the Noxfile with ``nox.options.force_venv_backend``. In case both are provided, the commandline argument takes precedence.

Finally note that the ``--no-venv`` flag is a shortcut for ``--force-venv-backend none`` and allows to temporarily run all selected sessions on the current python interpreter (the one running nox).

.. code-block:: console

    nox --no-venv

.. _opt-reuse-existing-virtualenvs:

Re-using virtualenvs
--------------------

By default, Nox deletes and recreates virtualenvs every time it is run. This is usually fine for most projects and continuous integration environments as `pip's caching <https://pip.pypa.io/en/stable/reference/pip_install/#caching>`_ makes re-install rather quick. However, there are some situations where it is advantageous to re-use the virtualenvs between runs. Use ``-r`` or ``--reuse-existing-virtualenvs``:

.. code-block:: console

    nox -r
    nox --reuse-existing-virtualenvs


If the Noxfile sets ``nox.options.reuse_existing_virtualenvs``, you can override the Noxfile setting from the command line by using ``--no-reuse-existing-virtualenvs``.

.. _opt-running-extra-pythons:

Running additional Python versions
----------------------------------
In addition to Nox supporting executing single sessions, it also supports runnings python versions that aren't specified using ``--extra-pythons``.

.. code-block:: console

    nox --extra-pythons 3.8 3.9

This will, in addition to specified python versions in the Noxfile, also create sessions for the specified versions.

This option can be combined with ``--python`` to replace, instead of appending, the Python interpreter for a given session::

    nox --python 3.10 --extra-python 3.10 -s lint

Also, you can specify ``python`` in place of a specific version. This will run the session
using the ``python`` specified for the current ``PATH``::

    nox --python python --extra-python python -s lint


.. _opt-stop-on-first-error:

Stopping if any session fails
-----------------------------

By default nox will continue to run all sessions even if one fails. You can use ``--stop-on-first-error`` to make nox abort as soon as the first session fails::

    nox --stop-on-first-error

If the Noxfile sets ``nox.options.stop_on_first_error``, you can override the Noxfile setting from the command line by using ``--no-stop-on-first-error``.


.. _opt-error-on-missing-interpreters:

Failing sessions when the interpreter is missing
------------------------------------------------

By default, Nox will skip sessions where the Python interpreter can't be found. If you want Nox to mark these sessions as failed, you can use ``--error-on-missing-interpreters``:

.. code-block:: console

    nox --error-on-missing-interpreters

If the Noxfile sets ``nox.options.error_on_missing_interpreters``, you can override the Noxfile setting from the command line by using ``--no-error-on-missing-interpreters``.

.. _opt-error-on-external-run:

Disallowing external programs
-----------------------------

By default Nox will warn but ultimately allow you to run programs not installed in the session's virtualenv. You can use ``--error-on-external-run`` to make Nox fail the session if it uses any external program without explicitly passing ``external=True`` into :func:`session.run <nox.session.Session.run>`:

.. code-block:: console

    nox --error-on-external-run

If the Noxfile sets ``nox.options.error_on_external_run``, you can override the Noxfile setting from the command line by using ``--no-error-on-external-run``.

Specifying a different configuration file
-----------------------------------------

If for some reason your noxfile is not named *noxfile.py*, you can use ``--noxfile`` or ``-f``:

.. code-block:: console

    nox --noxfile something.py
    nox -f something.py


.. _opt-envdir:

Storing virtualenvs in a different directory
--------------------------------------------

By default nox stores virtualenvs in ``./.nox``, however, you can change this using ``--envdir``:

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
    nox > Creating virtualenv using python3.7 in ./.nox/tests
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
set, nox will output in plaintext.

You can manually control Nox's output using the ``--nocolor`` and ``--forcecolor`` flags.

For example, this will always output colorful logs:

.. code-block:: console

    nox --forcecolor

However, this will never output colorful logs:

.. code-block:: console

    nox --nocolor


.. _opt-report:


Controlling commands verbosity
------------------------------

By default, Nox will only show output of commands that fail, or, when the commands get passed ``silent=False``.
By passing ``--verbose`` to Nox, all output of all commands run is shown, regardless of the silent argument.


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

    # Afterwards you can enable completion for nox:
    eval "$(register-python-argcomplete nox)"

tcsh

.. code-block:: console

    eval `register-python-argcomplete --shell tcsh nox`

fish

.. code-block:: console

    register-python-argcomplete --shell fish nox | .
