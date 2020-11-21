# Contributing

Thank you for your interest in improving Nox. Nox is open-source under the
[Apache License Version 2.0](http://www.apache.org/licenses/LICENSE-2.0) and welcomes contributions in the form of bug reports, feature requests, and pull requests.

Nox is hosted on [GitHub](https://github.com/theacodes/nox).

## Support, questions, and feature requests

Feel free to file a bug on [GitHub](https://github.com/theacodes/nox).

## Reporting issues

File a bug on [GitHub](https://github.com/theacodes/nox). To help us figure out what's going on, please err on the
side of including lots of information, such as:

* Operating system.
* Python version.
* If possible, a minimal case that can reproduce the issue.

## Pull requests

* It's recommended to file a bug before starting work on anything. It'll allow
  chance to talk it over with the owners and validate your approach.
* Nox maintains 100% test coverage. All pull requests must maintain this.
* Follow [pep8](https://pep8.org).
* Update documentation, if relevant.

## Running tests

Nox runs its own tests (it's recursive!). The best thing to do is start with
a known-good nox installation, e.g. from PyPI:

    pip install --pre --upgrade nox

To just check for lint errors, run:

    nox --session lint

To run against a particular Python version:

    nox --session tests-3.6
    nox --session tests-3.7
    nox --session tests-3.8
    nox --session tests-3.9


When you send a pull request Travis will handle running everything, but it is
recommended to test as much as possible locally before pushing.

## Getting a sticker

If you've contributed to Nox, you can get a cute little Nox sticker. Reach out to Thea at me@thea.codes to request one.

## Getting paid

Contributions to Nox can be expensed through [our Open Collective](https://opencollective.com/python-nox). The maintainers will let you know when and for how much you can expense contributions, but always feel free to ask. 
