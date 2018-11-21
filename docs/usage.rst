Command-line usage
==================

Invocation
----------

Nox is normally invoked on the command line::

    nox


You can also invoke Nox via the Python interpreter::

    python3 -m nox


Listing available sessions
--------------------------

To list all available sessions, including parametrized sessions::

    nox -l
    nox --list-sessions


.. _session_execution_order:

Running all sessions
--------------------

You can run every session by just executing `nox` without any arguments::

    nox

The order that sessions are executed is the order that they appear in the Noxfile.


.. _opt-sessions-and-keywords:

Specifying one or more sessions
-------------------------------

By default Nox will run all sessions defined in the noxfile. However, you can choose to run a particular set of them using ``--session``, ``-s``, or ``-e``::

    nox --session tests
    nox -s lint tests
    nox -e lint

You can also use the ``NOXSESSION`` environment variable::

    NOXSESSION=lint nox
    NOXSESSION=lint,tests nox

Nox will run these sessions in the same order they are specified.

You can also use `pytest-style keywords`_ to filter test sessions::

    nox -k "not lint"
    nox -k "tests and not lint"

.. _pytest-style keywords: https://docs.pytest.org/en/latest/usage.html#specifying-tests-selecting-tests


.. _running_paramed_sessions:

Specifying parametrized sessions
--------------------------------

If you have a :ref:`parametrized <parametrized>` session such as::

    @nox.parametrize('django', ['1.9', '2.0'])
    def tests(session, django):
        ...

Then running ``nox --session tests`` will actually run all parametrized versions of the session. If you want the run the session with a particular set of parametrized arguments, you can specify them with the session name::

    nox --session "tests(django='1.9')"
    nox --session "tests(django='2.0')"


.. _opt-reuse-existing-virtualenvs:

Re-using virtualenvs
--------------------

By default nox deletes and recreates virtualenvs every time it is run. This is usually fine for most projects and continuous integration environments as `pip's caching <https://pip.pypa.io/en/stable/reference/pip_install/#caching>`_ makes re-install rather quick. However, there are some situations where it is advantageous to re-use the virtualenvs between runs. Use ``-r`` or ``--reuse-existing-virtualenvs``::

    nox -r
    nox --reuse-existing-virtualenvs


If the Noxfile sets ``nox.options.reuse_existing_virtualenvs``, you can override the Noxfile setting from the command line by using ``--no-reuse-existing-virtualenvs``.

.. _opt-stop-on-first-error:

Stopping if any session fails
-----------------------------

By default nox will continue to run all sessions even if one fails. You can use ``--stop-on-first-error`` to make nox abort as soon as the first session fails::

    nox --stop-on-first-error

If the Noxfile sets ``nox.options.stop_on_first_error``, you can override the Noxfile setting from the command line by using ``--no-stop-on-first-error``.

.. _opt-error-on-missing-interpreters:

Failing sessions when the interpreter is missing
------------------------------------------------

By default, Nox will skip sessions where the Python interpreter can't be found. If you want Nox to mark these sessions as failed, you can use ``--error-on-missing-interpreters``::

    nox --error-on-missing-interpreters

If the Noxfile sets ``nox.options.error_on_missing_interpreters``, you can override the Noxfile setting from the command line by using ``--no-error-on-missing-interpreters``.

.. _opt-error-on-external-run:

Disallowing external programs
-----------------------------

By default Nox will warn but ultimately allow you to run programs not installed in the session's virtualenv. You can use ``--error-on-external-run`` to make Nox fail the session if it uses any external program without explicitly passing ``external=True`` into :func:`session.run <nox.session.Session.run>`::

    nox --error-on-external-run

If the Noxfile sets ``nox.options.error_on_external_run``, you can override the Noxfile setting from the command line by using ``--no-error-on-external-run``.

Specifying a different configuration file
-----------------------------------------

If for some reason your noxfile is not named *noxfile.py*, you can use ``--noxfile`` or ``-f``::

    nox --noxfile something.py
    nox -f something.py


.. _opt-envdir:

Storing virtualenvs in a different directory
--------------------------------------------

By default nox stores virtualenvs in ``./.nox``, however, you can change this using ``--envdir``::

    nox --envdir /tmp/.


Skipping everything but install commands
----------------------------------------

There are a couple of cases where it makes sense to have Nox only run ``install`` commands, such as preparing an environment for offline testing or re-creating the same virtulenvs used for testing. You can use ``--install-only`` to skip ``run`` commands.

For example, given this Noxfile:

.. code-block:: python

    @nox.session
    def tests(session):
        session.install("pytest")
        session.install(".")
        session.run("pytest")


Running:

.. code-block:: bash

    nox --install-only


Would run both ``install`` commands, but skip the ``run`` command::

.. code-block:: plaintext


    nox > Running session tests
    nox > Creating virtualenv using python3.7 in ./.nox/tests
    nox > pip install --upgrade pytest
    nox > pip install --upgrade .
    nox > Skipping pytest run, as --install-only is set.
    nox > Session tests was successful.


Controlling color output
------------------------

By default, Nox will output colorful logs if you're using in an interactive
terminal. However, if you are redirecting ``stderr`` to a file or otherwise
not using an interactive terminal, nox will output in plaintext.

You can manually control Nox's output using the ``--nocolor`` and ``--forcecolor`` flags.

For example, this will always output colorful logs::

    nox --forcecolor

However, this will never output colorful logs::

    nox --nocolor


.. _opt-report:

Outputting a machine-readable report
------------------------------------

You can output a report in ``json`` format by specifying ``--report``::

    nox --report status.json


Windows
-------

Nox has provisional support for running on Windows. However, depending on your Windows, Python, and virtualenv versions there may be issues. See the following threads for more info:

* `tox issue 260 <https://github.com/tox-dev/tox/issues/260>`_
* `Python issue 24493 <http://bugs.python.org/issue24493>`_
* `Virtualenv issue 774 <https://github.com/pypa/virtualenv/issues/774>`_

The Python binaries on Windows are found via the Python `Launcher`_ for
Windows (``py``). For example, Python 3.5 can be found by determining which
executable is invoked by ``py -3.5``. If a given test needs to use the 32-bit
version of a given Python, then ``X.Y-32`` should be used as the version.

.. _Launcher: https://docs.python.org/3/using/windows.html#python-launcher-for-windows


Converting from tox
-------------------

Nox has experimental support for converting ``tox.ini`` files into ``noxfile.py`` files. This doesn't support every feature of tox and is intended to just do most of the mechanical work of converting over- you'll likely still need to make a few changes to the converted ``noxfile.py``.

To use the converter, install ``nox`` with the ``tox_to_nox`` extra::

    pip install --upgrade nox[tox_to_nox]

Then, just run ``tox-to-nox`` in the directory where your ``tox.ini`` resides::

    tox-to-nox

This will create a ``noxfile.py`` based on the environments in your ``tox.ini``. Some things to note:

- `Generative environments`_ work, but will be converted as individual environments. ``tox-to-nox`` isn't quite smart enough to turn these into :ref:`parametrized <running_paramed_sessions>` sessions, but it should be straightforward to manually pull out common configuration for parametrization.
- Due to the way tox parses its configuration, all `substitutions`_ are baked in when converting. This means you'll need to replace the static strings in the ``noxfile.py`` with appropriate variables.
- Several non-common tox options aren't implemented, but it's possible to do so. Please file a feature request if you run into one you think will be useful.

.. _Generative environments: http://tox.readthedocs.io/en/latest/config.html#generating-environments-conditional-settings
.. _substitutions: http://tox.readthedocs.io/en/latest/config.html#substitutions
