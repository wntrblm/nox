Usage
=====

Nox is normally invoked on the command line::

    nox

Specifying a different configuration file
-----------------------------------------

If for some reason your noxfile is not named *nox.py*, you can use ``--noxfile`` or ``-f``::

    nox --noxfile something.py
    nox -f something.py


Storing virtualenvs in a different directory
--------------------------------------------

By default nox stores virtualenvs in ``./.nox``, however, you can change this using ``--envdir``::

    nox --envdir /tmp/.nox


Specifying one or more sessions
-------------------------------

By default nox will run all session defined in the noxfile. However, you can choose to run a particular set of them using ``--session``, ``-s``, or ``-e``:

    nox --session py27
    nox -s lint py27
    nox -e py34


Re-using virtualenvs
--------------------

By default nox deletes and recreates virtualenvs every time it is run. This is usually fine for most projects and continuous integration environments as `pip's caching <https://pip.pypa.io/en/stable/reference/pip_install/#caching>`_ makes re-install rather quick. However, there are some situations where it is advantageous to re-use the virtualenvs between runs. Use ``-r`` or ``--reuse-existing-virtualenvs``::

    nox -r
    nox --reuse-existing-virtualenvs


Stopping if any session fails
-----------------------------

By default nox will continue to run all sessions even if one fails. You can use ``--stop-on-first-error`` to make nox abort as soon as the first session fails::

    nox --stop-on-first-error


Windows
-------

Nox has provisional support for running on Windows. However, depending on your Windows, Python, and virtualenv versions there may be issues. See the following threads for more info:

* `Tox issue 260 <https://bitbucket.org/hpk42/tox/issues/260/fatal-python-error-when-running-32bit>`_
* `Python issue 24493 <http://bugs.python.org/issue24493>`_
* `Virtualenv issue 774 <https://github.com/pypa/virtualenv/issues/774>`_

