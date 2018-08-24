Command-line usage
==================

Nox is normally invoked on the command line::

    nox


You can also invoke nox via the Python interpreter::

    python3 -m nox


Specifying a different configuration file
-----------------------------------------

If for some reason your noxfile is not named *noxfile.py*, you can use ``--noxfile`` or ``-f``::

    nox --noxfile something.py
    nox -f something.py


Storing virtualenvs in a different directory
--------------------------------------------

By default nox stores virtualenvs in ``./.nox``, however, you can change this using ``--envdir``::

    nox --envdir /tmp/.


Listing available sessions
--------------------------

To list all available sessions, including parametrized sessions::

    nox -l
    nox --list-sessions

.. _session_execution_order:

Running all sessions
--------------------

You can run every session by just executing `nox` without any arguments:

    nox

The order that sessions are executed is the order that they appear in the Noxfile.

Specifying one or more sessions
-------------------------------

By default nox will run all sessions defined in the noxfile. However, you can choose to run a particular set of them using ``--session``, ``-s``, or ``-e``::

    nox --session tests
    nox -s lint tests
    nox -e lint

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
    def session_tests(session, django):
        ...

Then running ``nox --session tests`` will actually run all parametrized versions of the session. If you want the run the session with a particular set of parametrized arguments, you can specify them with the session name::

    nox --session "tests(django='1.9')"
    nox --session "tests(django='2.0')"


Re-using virtualenvs
--------------------

By default nox deletes and recreates virtualenvs every time it is run. This is usually fine for most projects and continuous integration environments as `pip's caching <https://pip.pypa.io/en/stable/reference/pip_install/#caching>`_ makes re-install rather quick. However, there are some situations where it is advantageous to re-use the virtualenvs between runs. Use ``-r`` or ``--reuse-existing-virtualenvs``::

    nox -r
    nox --reuse-existing-virtualenvs


Stopping if any session fails
-----------------------------

By default nox will continue to run all sessions even if one fails. You can use ``--stop-on-first-error`` to make nox abort as soon as the first session fails::

    nox --stop-on-first-error


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

Windows
-------

Nox has provisional support for running on Windows. However, depending on your Windows, Python, and virtualenv versions there may be issues. See the following threads for more info:

* `Tox issue 260 <https://github.com/tox-dev/tox/issues/260>`_
* `Python issue 24493 <http://bugs.python.org/issue24493>`_
* `Virtualenv issue 774 <https://github.com/pypa/virtualenv/issues/774>`_


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
