The Nox Cookbook
================

The What?
---------

A lot of people and a lot of projects use Nox for their python automation powers.

Some of these sessions are the classic "run pytest and linting", some are more unique and more interesting!

The Nox cookbook is a collection of these sessions.

Nox is super easy to get started with, and super powerful right out of the box. But when things get complex or you want to chain together some more powerful tasks, often the only examples can be found hunting around GitHub for novel sessions.

The kind of sessions that make you think "I didn't know you could do that!"

This cookbook is intended to be a centralized, community-driven repository of awesome Nox sessions to act as a source of inspiration and a reference guide for Nox's users. If you're doing something cool with Nox, why not add your session here?


Contributing a Session
----------------------

Anyone can contribute sessions to the cookbook. However, there are a few guiding principles you should keep in mind:

* Your session should be interesting or unique, it should do something out of the ordinary or otherwise interesting.
* You should explain briefly what it does and why it's interesting.

For general advice on how to contribute to Nox see our :doc:`CONTRIBUTING` guide

Recipes
-------

Instant Dev Environment
^^^^^^^^^^^^^^^^^^^^^^^

A common sticking point in contributing to python projects (especially for beginners) is the problem of wrangling virtual environments and installing dependencies.

Enter the ``dev`` nox session:

.. code-block:: python

    import nox


    # It's a good idea to keep your dev session out of the default list
    # so it's not run twice accidentally
    @nox.session(default=False)
    def dev(session: nox.Session) -> None:
        """
        Set up a python development environment for the project at ".venv".
        """

        session.install("virtualenv")

        session.run("virtualenv", ".venv", silent=True)

        # Use the venv's interpreter to install the project along with
        # all it's dev dependencies, this ensures it's installed in the right way
        session.run(".venv/bin/pip", "install", "-e", ".[dev]", external=True)

With this, a user can simply run ``nox -s dev`` and have their entire environment set up automatically!


The Auto-Release
^^^^^^^^^^^^^^^^

Releasing a new version of an open source project can be a real pain, with lots of intricate steps. Tools like `Bump2Version <https://github.com/c4urself/bump2version>`_ really help here.

Even more so with a sprinkling of Nox:

.. code-block:: python

    import argparse
    import nox

    @nox.session
    def release(session: nox.Session) -> None:
        """
        Kicks off an automated release process by creating and pushing a new tag.

        Invokes bump2version with the posarg setting the version.

        Usage:
        $ nox -s release -- [major|minor|patch]
        """
        parser = argparse.ArgumentParser(description="Release a semver version.")
        parser.add_argument(
            "version",
            type=str,
            nargs=1,
            help="The type of semver release to make.",
            choices={"major", "minor", "patch"},
        )
        args: argparse.Namespace = parser.parse_args(args=session.posargs)
        version: str = args.version.pop()

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


Using a lockfile
^^^^^^^^^^^^^^^^

If you use a tool like ``uv`` to lock your dependencies, you can use that inside a nox session. Here's an example:

.. code-block:: python

    @nox.session(venv_backend="uv")
    def tests(session: nox.Session) -> None:
        """
        Run the unit and regular tests.
        """
        session.run_install(
            "uv",
            "sync",
            "--extra=test",
            "--no-default-extras",
            f"--python={session.virtualenv.location}",
            env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
        )
        session.run("pytest", *session.posargs)


Here we run ``uv sync`` on the nox virtual environment. Other useful flags might include ``--locked`` (validate lockfile is up-to-date) and ``--inexact`` (will allow you to install other packages as well).

The `nox-uv <https://github.com/dantebben/nox-uv>`_ package can be used to reduce the boilerplate needed to ``uv sync`` specific dependency groups or extras into the nox virtual environment.
By default, ``nox-uv`` also validates that the lockfile is up-to-date.

.. code-block:: python

    #!/usr/bin/env -S uv run --script --quiet

    # /// script
    # dependencies = ["nox", "nox-uv"]
    # ///

    import nox
    import nox_uv

    nox.options.default_venv_backend = "uv"

    @nox_uv.session(
        python=["3.10", "3.11", "3.12", "3.13"],
        uv_groups=["test"],
    )
    def test(s: nox.Session) -> None:
        """`uv sync` main dependencies and the `test` dependency group."""
        s.run("python", "-m", "pytest")

    @nox_uv.session(uv_groups=["type_check"])
    def type_check(s: nox.Session) -> None:
        """`uv sync` main dependencies and the `type_check` dependency group."""
        s.run("mypy", "src")

    @nox_uv.session(uv_only_groups=["lint"])
    def type_check(s: nox.Session) -> None:
        """`uv sync` only the `lint` dependency group."""
        s.run("ruff", "check", ".")
        s.run("ruff", "format", "--check", ".")


    if __name__ == "__main__":
        nox.main()


Generating a matrix with GitHub Actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Nox knows what sessions it needs to run. Why not tell GitHub Actions what jobs to run dynamically? Using the ``--json`` flag and a bit of json processing, it's easy:

.. code-block:: yaml

    jobs:
      generate-jobs:
        runs-on: ubuntu-latest
        outputs:
          session: ${{ steps.set-matrix.outputs.session }}
        steps:
        - uses: actions/checkout@v3
        - uses: wntrblm/nox@main
        - id: set-matrix
          shell: bash
          run: echo session=$(nox --json -l | jq -c '[.[].session]') | tee --append $GITHUB_OUTPUT
      checks:
        name: Session ${{ matrix.session }}
        needs: [generate-jobs]
        runs-on: ubuntu-latest
        strategy:
          fail-fast: false
          matrix:
            session: ${{ fromJson(needs.generate-jobs.outputs.session) }}
        steps:
        - uses: actions/checkout@v3
        - uses: wntrblm/nox@main
        - run: nox -s "${{ matrix.session }}"
