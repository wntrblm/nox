## 2018.8.23

**Heads up!** This is a very big release for Nox. Please read these release notes thoroughly and reach out to us on GitHub if you run into issues.

Breaking changes and other important notes:

* Nox is now published as "nox" on PyPI. This means that Nox is installed via `pip install nox` instead of `nox-automation`. Since the new release makes so many breaking changes, we won't be updating the old `nox-automation` package.
* Nox's configuration file is now called `noxfile.py` instead of `nox.py`.
* Nox no longer supports Python 2.7. You can still create and run Python 2.7 sessions, but Nox itself must be installed using Python 3.5+.
* Nox's behavior has been changed from *declarative*  to *imperative*. Session actions now run immediately. Existing code to setup session virtualenv, such as `session.interpreter` **will break**! Please consult the documention on how to use `@nox.session(python=[...])` to configure virtualenvs for sessions.
* Nox now uses calver for releases.
* Support for the legacy naming convention (for example, `session_tests`) has been removed.

Other changes:

* Update colorlog dependency range.
* Update installation command in contributing. (#101)
* Remove Python 2.x object inheritance. (#109)
* Fix python syntax error on docs. (#111)
* Show additional links on PyPI. (#108)
* Add contributors file. (#113)
* Run sphinx with -W option. (#115)
* Using `os.pathsep` instead of a hardcoded `':'`. (#105)
* Use a configuration file for readthedocs. (#107)
* Add 'py' alias for `nox.session(python=...)`.
* Fix processing of numeric Python versions that specify a patch version.
* Use Black to format code.
* Support invoking Nox using `python -m nox`.
* Produce better error message when sessions can't be found.
* Fix missing links in README.rst.
* Remove usage of future imports.
* Remove usage of six.
* Make session.install a simple alias for session.run.
* Refactor nox.command.Command as nox.command.run, reducing complexity.
* Add list of projects that use Nox.
* Use witchhazel pygments theme.

## v0.19.1

**Note**:: v0.19.1 was the last version released as "nox-automation" on PyPI. Subsequent releases are published as "nox".

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
