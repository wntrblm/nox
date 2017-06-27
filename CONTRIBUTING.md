# Contributing to Nox

Thank you for your interest in improving Nox. Nox is open-source under the
Apache License Version 2.0 and welcomes contributions.

## Support, questions, and feature requests

Feel free to file a bug on github.

## Reporting issues

File a bug on github. To help us figure out what's going on, please err on the
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

    pip install --upgrade nox-automation

To just check for lint errors, run:

    nox --session lint

To run against a particular Python version:

    nox --session "interpreters(version='2.7')"
    nox --session "interpreters(version='3.4')"
    nox --session "interpreters(version='3.5')"
    nox --session "interpreters(version='3.6')"

When you send a pull request Travis will handle running everything, but it is
recommended to test as much as possible locally before pushing.
