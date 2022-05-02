<p align="center">
<img src="https://github.com/wntrblm/nox/raw/main/docs/_static/alice.png" alt="logo" width=50%>
</p>

# Nox

[![License](https://img.shields.io/github/license/wntrblm/nox)](https://github.com/wntrblm/nox)
[![PyPI](https://img.shields.io/pypi/v/nox.svg?logo=python)](https://pypi.python.org/pypi/nox)
[![GitHub](https://img.shields.io/github/v/release/wntrblm/nox?logo=github&sort=semver)](https://github.com/wntrblm/nox)
[![Code Style](https://img.shields.io/badge/code%20style-black-black)](https://github.com/wntrblm/nox)
[![CI](https://github.com/wntrblm/nox/workflows/CI/badge.svg)](https://github.com/wntrblm/nox/actions?query=workflow%3ACI)
[![Downloads](https://static.pepy.tech/personalized-badge/nox?period=total&units=international_system&left_color=grey&right_color=green&left_text=Downloads)](https://pepy.tech/project/nox)

*Flexible test automation with Python*

* **Documentation:** [https://nox.readthedocs.io](https://nox.readthedocs.io)

* **Source Code:** [https://github.com/wntrblm/nox](https://github.com/wntrblm/nox)

## Overview

`nox` is a command-line tool that automates testing in multiple Python environments, similar to [tox]. Unlike tox, Nox uses a standard Python file for configuration:

```python
import nox


@nox.session
def tests(session: nox.Session) -> None:
    session.install("pytest")
    session.run("pytest")

@nox.session
def lint(session: nox.Session) -> None:
    session.install("flake8")
    session.run("flake8", "--import-order-style", "google")
```

## Installation

Nox is designed to be installed globally (not in a project virtual environment), the recommended way of doing this is via [pipx], a tool designed to install python CLI programs whilst keeping them separate from your global or system python.

To install Nox with [pipx]:

```shell
pipx install nox
```

You can also use [pip] in your global python:

```shell
python3 -m pip install nox
```

You may want to user the [user-site] to avoid messing with your Global python install:

```shell
python3 -m pip install --user nox
```

## Usage

### List all sessions

```shell
nox -l/--list
```

### Run all sessions

```shell
nox
```

### Run a particular session

```shell
nox -s/--session test
```

Checkout the [docs](https://nox.readthedocs.io) for more! 🎉

## Contributing

Nox is an open source project and welcomes contributions of all kinds, checkout the [contributing guide](CONTRIBUTING.md) for help on how to help us out!

All contributors must follow the [code of conduct](CODE_OF_CONDUCT.md) and be nice to one another! 😃

[tox]: https://tox.readthedocs.io
[pipx]: https://pypa.github.io/pipx/
[pip]: https://pip.pypa.io/en/stable/
[user-site]: https://packaging.python.org/en/latest/tutorials/installing-packages/#installing-to-the-user-site
