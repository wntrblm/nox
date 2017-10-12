## v0.18.2

* On Windows, use the `py.exe` [launcher][2] (e.g. `py.exe -2.7`) to locate
  Python executables. ([#53][1])

## v0.18.1

* Fix nox not returning a non-zero exit code on failure. (#55)
* Restore result and report output. (#57)

## v0.18.0

* Blacklist problematic virtualenv environment variables (#49)
* Use `python -m virtualenv` to invoke virtualenv (#47)
* Making sure all `Command`s use run in `__call__`. (#48)
* Addition of `session.notify`. (#39)
* Refactor the list of sessions into a manifest class. (#38)
* Changed some instances of session to be plural (#37)
* Small documentation updates (#36)

[1]: https://github.com/jonparrott/nox/pull/53
[2]: https://docs.python.org/3/using/windows.html#launcher
