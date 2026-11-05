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

Enter the ``dev`` nox environment:

.. code-block:: python

    import nox

    # The location puts the environment where your editor expects to find it.
    dev = nox.env("dev", dependencies=["-e.[dev]"], location=".venv")


With this, a user can run ``nox -s dev`` to set up their entire environment. The environment has no tasks, so Nox only provisions it, and a bare ``nox`` run skips it.

Nox skips the install on later runs if the inputs are unchanged. ``pyproject.toml`` is an input, so a change to it recreates the environment. If the project has a ``uv.lock``, use it instead, and Nox re-syncs the environment in place when the lock file changes:

.. code-block:: python

    dev = nox.env.uv("dev", groups=["dev"], location=".venv")


Sharing an environment between tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Put tools that can share packages in one :ref:`environment <environments>` and attach each job as a task:

.. code-block:: python

    import nox

    tooling = nox.env("tooling", dependencies=["ruff", "mypy"])


    @tooling.task
    def lint(session: nox.Session) -> None:
        """Lint the code."""
        session.run("ruff", "check", ".", *session.posargs)


    @tooling.task
    def format(session: nox.Session) -> None:
        """Check the code formatting."""
        session.run("ruff", "format", "--check", ".")


    @tooling.task(explicit=True)
    def typecheck(session: nox.Session) -> None:
        """Run the type checker."""
        session.run("mypy", "src")


    nox.alias("check", "tooling:lint", "tooling:typecheck")

Now ``nox -s tooling`` runs the non-explicit tasks, ``nox -s tooling:typecheck`` runs one task, and ``nox -s check`` runs the alias. All use the same virtual environment.


The Auto-Release
^^^^^^^^^^^^^^^^

Releasing a new version of an open source project can be a real pain, with lots of intricate steps. Tools like `Bump My Version <https://github.com/callowayproject/bump-my-version>`_ really help here.

Even more so with a sprinkling of Nox:

.. code-block:: python

    import argparse
    import nox

    @nox.session
    def release(session: nox.Session) -> None:
        """
        Kicks off an automated release process by creating and pushing a new tag.

        Invokes bump-my-version with the posarg selecting the version part.

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


        session.install("bump-my-version")

        session.log(f"Bumping the {version!r} version")
        session.run("bump-my-version", "bump", version)

        session.log("Pushing the new tag")
        session.run("git", "push", external=True)
        session.run("git", "push", "--tags", external=True)

Now a simple ``nox -s release -- patch`` will automate your release (provided you have Bump My Version set up to change your files). This is especially powerful if you have a CI/CD pipeline set up!


Using a lockfile
^^^^^^^^^^^^^^^^

If you use ``uv`` to lock your dependencies, ``nox.env.uv`` runs ``uv sync --locked`` on the nox virtual environment:

.. code-block:: python

    import nox

    tests = nox.env.uv("tests", python=["3.12", "3.13"], groups=["test"])


    @tests.task
    def run(session: nox.Session) -> None:
        """
        Run the unit and regular tests.
        """
        session.run("pytest", *session.posargs)

Nox syncs only when the lockfile changes. See :ref:`environments` for the options.

For a :pep:`751` lockfile, use ``nox.env.pylock``:

.. code-block:: python

    tests = nox.env.pylock("tests", lockfile="pylock.toml", groups=["test"])

If you prefer ``@nox.session``, the `nox-uv <https://github.com/dantebben/nox-uv>`_ package can be used to reduce the boilerplate needed to ``uv sync`` specific dependency groups or extras into the nox virtual environment.
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
    def lint(s: nox.Session) -> None:
        """`uv sync` only the `lint` dependency group."""
        s.run("ruff", "check", ".")
        s.run("ruff", "format", "--check", ".")


    if __name__ == "__main__":
        nox.main()


Testing on every supported Python
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``Programming Language :: Python :: 3.X`` trove classifiers in
``pyproject.toml`` already list every Python your project supports.
:func:`nox.project.python_versions` reads them, so the session matrix follows
the classifiers without a second copy of the list. If the project also has a
``Programming Language :: Python :: Free Threading`` classifier, the
non-experimental free-threaded builds (``3.14t`` and newer) are added too:

.. code-block:: toml

    [project]
    classifiers = [
      "Programming Language :: Python :: 3.12",
      "Programming Language :: Python :: 3.13",
      "Programming Language :: Python :: 3.14",
      "Programming Language :: Python :: 3.15",
      "Programming Language :: Python :: Free Threading :: 3 - Stable",
    ]

.. code-block:: python

    import nox

    PYPROJECT = nox.project.load_toml("pyproject.toml")
    # ["3.12", "3.13", "3.14", "3.14t, "3.15", "3.15t"]
    ALL_PYTHON = nox.project.python_versions(PYPROJECT)


    @nox.session(python=ALL_PYTHON)
    def tests(session: nox.Session) -> None:
        session.install("-e.", "pytest")
        session.run("pytest")

Pass ``free_threaded=False`` to leave the free-threaded builds out, or
``free_threaded=True`` to add them without the classifier. 3.13t is never
added automatically, as free threading was experimental in 3.13.


Combining coverage across Python versions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Code paths can vary between Python versions, so measuring each test run separately
and then combining the data gives a more accurate coverage report. The important
parts are to remove stale data before the matrix starts, give every run a unique
data file, and combine the files only after every test session finishes:

.. code-block:: python

    import nox

    PYPROJECT = nox.project.load_toml("pyproject.toml")
    PYTHON_VERSIONS = nox.project.python_versions(PYPROJECT)

    coverage = nox.env("coverage", dependencies=["coverage[toml]"])
    tests = nox.env(
        "tests",
        python=PYTHON_VERSIONS,
        dependencies=["coverage[toml]", "--group=test", "-e."],
    )


    @coverage.task(explicit=True)
    def erase(session: nox.Session) -> None:
        """Remove data left by an earlier coverage run."""
        session.run("coverage", "erase")


    @tests.task(requires=["coverage:erase"])
    def run(session: nox.Session) -> None:
        """Measure tests independently for each supported Python version."""
        session.run(
            "coverage",
            "run",
            "-m",
            "pytest",
            *session.posargs,
            env={"COVERAGE_FILE": f".coverage.{session.python}"},
        )


    @coverage.task(requires=["tests"])
    def report(session: nox.Session) -> None:
        """Combine the per-version data and display one report."""
        session.run("coverage", "combine")
        session.run("coverage", "report", "--show-missing")

Running ``nox -s coverage`` selects ``coverage:report``; its requirements run
cleanup first and then the ``run`` task on every Python version. ``coverage combine``
writes the combined ``.coverage`` data file and removes the per-version files it
consumed.
The project is an editable install (``-e.``) because Nox does not reinstall when
only your source code changes.
Keep the phases sequential so cleanup and reporting cannot race with the test
sessions. Projects that use subprocesses or pytest-xdist should also enable
Coverage.py's `parallel mode <https://coverage.readthedocs.io/en/latest/config.html#run-parallel>`_.


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
