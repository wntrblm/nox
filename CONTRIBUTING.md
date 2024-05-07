# Contributing

Thank you for your interest in improving Nox. Nox is open-source under the
[Apache License Version 2.0](http://www.apache.org/licenses/LICENSE-2.0) and welcomes contributions in the form of bug reports, feature requests, and pull requests.

Nox is hosted on [GitHub](https://github.com/wntrblm/nox).

## Support, questions, and feature requests

Feel free to file a bug or feature request on [GitHub](https://github.com/wntrblm/nox). If your question is more general or does not fit neatly into one of those categories, we also have a Nox channel on the [Winterbloom Discord server](https://discord.com/invite/UpfqghQ).

You should find a permalink to the invite when you raise a new issue on GitHub.

## Reporting issues

File a bug on [GitHub](https://github.com/wntrblm/nox). To help us figure out what's going on, please err on the
side of including lots of information, such as:

* Operating system.
* Python version.
* If possible, a minimal case that can reproduce the issue.

## Pull requests

* It's recommended to file a bug before starting work on anything. It'll allow
  chance to talk it over with the owners and validate your approach.
* Nox maintains 100% test coverage. All pull requests must maintain this.
* Follow [pep8](https://pep8.org).
* Update documentation and tests if relevant.
* Ensure your changes pass Nox's tests and lint suites before pushing.

## Running tests

Nox runs its own tests (it's recursive!). The best thing to do is start with
a known-good Nox installation, e.g. from PyPI:

    pip install --pre --upgrade nox

To just check for lint errors, run:

    nox --session lint

To run against a particular Python version:

    nox --session tests-3.8
    nox --session tests-3.9
    nox --session tests-3.10
    nox --session tests-3.11
    nox --session tests-3.12

When you send a pull request the CI will handle running everything, but it is
recommended to test as much as possible locally before pushing.

## Getting a sticker

If you've contributed to Nox, you can get a cute little Nox sticker. Reach out to Thea at me@thea.codes to request one.

## Getting paid

Contributions to Nox can be expensed through [our Open Collective](https://opencollective.com/python-nox). The maintainers will let you know when and for how much you can expense contributions, but always feel free to ask.
