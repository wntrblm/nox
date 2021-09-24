The Nox Cookbook
================

The What?
---------

A lot of people and a lot of projects use ``nox`` for their python automation powers.

Some of these sessions are the classic "run pytest and linting", some are more unique and more interesting!

The nox cookbook is a collection of these such sessions.

``nox`` is super easy to get started with, and super powerful right out of the box. But when things get complex or you want to chain together some more powerful tasks, often the only examples can be found hunting around GitHub for novel ``nox`` sessions.

The kind of sessions that make you think "I didn't know you could do that!"

This cookbook is intended to be a centralized, community-driven repository of awesome ``nox`` sessions to act as a source of inspiration and a reference guide for nox's users. If you're doing something cool with ``nox``, why not add your session here?


Contributing a Session
----------------------

Anyone can contribute sessions to the cookbook. However, there are a few guiding principles you should keep in mind:

* Your session should be interesting or unique, it should do something out of the ordinary or otherwise interesting.
* You should explain briefly what it does and why it's interesting.
* You should include the full session as a code block, if it's too large, try to include a minimal example. Bonus points if a user can copy and paste it into their ``noxfile.py`` and run it straight away!


And now on with the recipes...

Recipes
-------

Instant Dev Environment
^^^^^^^^^^^^^^^^^^^^^^^

A common sticking point in contributing to python projects (especially for beginners) is the problem of wrangling virtual environments and installing dependencies.

Enter the ``dev`` nox session:

.. code-block:: python

    import os
    
    import nox

    # It's a good idea to keep your dev session out of the default list
    # so it's not run twice accidentally
    nox.options.sessions = [<sessions other than dev>]

    @nox.session
    def dev(session: nox.Session) -> None:
        """
        Sets up a python development environment for the project.

        This session will:
        - Create a python virtualenv for the session
        - Install the `virtualenv` cli tool into this environment
        - Use `virtualenv` to create a global project virtual environment
        - Invoke the python interpreter from the global project environment to install
          the project and all it's development dependencies.
        """

        session.install("virtualenv")
        # VENV_DIR here is a pathlib.Path location of the project virtualenv
        # e.g. .venv
        session.run("virtualenv", os.fsdecode(VENV_DIR), silent=True)

        python = os.fsdecode(VENV_DIR.joinpath("bin/python"))

        # Use the venv's interpreter to install the project along with
        # all it's dev dependencies, this ensures it's installed in the right way
        session.run(python, "-m", "pip", "install", "-e", ".[dev]", external=True)

With this, a user can simply run ``nox -s dev`` and have their entire environment set up automatically!


The Auto-Release
^^^^^^^^^^^^^^^^

Releasing a new version of an open source project can be a real pain, with lots of intricate steps. Tools like `Bump2Version <https://github.com/c4urself/bump2version>`_ really help here.

Even more so with a sprinkling of ``nox``:

.. code-block:: python

    import nox

    @nox.session
    def release(session: nox.Session) -> None:
        """
        Kicks off an automated release process by creating and pushing a new tag.

        Invokes bump2version with the posarg setting the version.
        
        Usage:
        $ nox -s release -- [major|minor|patch]
        """

        allowed_args = {"major", "minor", "patch"}
        n_args = len(session.posargs)

        # Ensure the correct args are passed
        if n_args != 1:
            session.error(
                f"Only 1 session arg allowed, got {n_args}. Pass one of: {allowed_args}"
            )

        # If we get here, we know there's only 1 posarg
        version = session.posargs.pop()

        if version not in allowed_args:
            session.error(
                f"Invalid argument: got {version!r}, expected one of: {allowed_args}"
            )

        # If we get here, we should be good to go
        # Let's do a final check for safety
        confirm = input(
            f"You are about to bump the {version!r} version. Are you sure? [y/n]: "
        )

        # Abort on anything other than 'y'
        if confirm.lower().strip() != "y":
            session.error(f"You said no when prompted to bump the {version!r} version.")


        session.install("bump2version")

        session.log(f"Bumping the {version!r} version")
        session.run("bump2version", version)

        session.log("Pushing the new tag")
        session.run("git", "push", external=True)
        session.run("git", "push", "--tags", external=True)

Now a simple ``nox -s release -- patch`` will automate your release (provided you have Bump2Version set up to change your files). This is especially powerful if you have a CI/CD pipeline set up!