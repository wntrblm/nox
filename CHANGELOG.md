## Pre-releases

### 2018.7.31dev1

Important notes and breaking changes:

* Nox no longer supports Python 2.7. You can still create and run Python 2.7 sessions, but Nox itself must be installed using Python 3.5+.
* Nox's behavior has been changed from *declarative*  to *imperative*. Session actions now run immediately. Existing code to setup session virtualenv, such as `session.interpreter` **will break**! Please consult the documention on how to use `@nox.session(python=[...])` to configure virtualenvs for sessions.
* Nox now uses calver for releases.
* Support for the legacy naming convention (for example, `session_tests`) has been removed.

Other notes:

* Add note about pre-releases.
* Fix missing links in Readme.
* Remove usage of future imports.
* Remove usage of six.
* Make session.install a simple alias for session.run.
* Refactor nox.command.Command as nox.command.run, reducing complexity.
* Add list of projects that use Nox

## v0.19.1

* Updates copyright information and contact addresses. No code changes.

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
