## v0.19.0

* Add missing parameter in docs (#89)
* Don't skip install commands when re-using existing virtualenvs. (#86)
* Add --nocolor and --forcecolor options (#85)
* Simulating `unittest.mock` backport in the Python 2 standard library. (#81)
* Fixing tox-to-nox docs reference. (#80)
* Removing patch of `py.exe` on AppVeyor. (#74)
* Adding Python 3.6 to AppVeyor. (#69)
* Adding AppVeyor badge to README. (#70)

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

[1]: https://github.com/theacodes/nox/pull/53
[2]: https://docs.python.org/3/using/windows.html#launcher
