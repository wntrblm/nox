# Changelog

## 2020.12.31
- Fix `NoxColoredFormatter.format`(#374)
- Use conda remove to clean up existing conda environments (#373)
- Support users specifying an undeclared parametrization of python via `--extra-python` (#361)
- Support double-digit minor version in `python` keyword (#367)
- Add `py.typed` to `manifest.in` (#360)
- Update nox to latest supported python versions. (#362)
- Decouple merging of `--python` with `nox.options` from `--sessions` and `--keywords` (#359)
- Do not merge command-line options in place (#357)

## 2020.8.22

- `conda_install` and `install` args are now automatically double-quoted when needed. (#312)
- Offline mode is now auto-detected by default by `conda_install`. This allows users to continue executing Nox sessions on already installed environments. (#314)
- Fix the default paths for Conda on Windows where the `python.exe` found was not the correct one. (#310)
- Add the `--add-timestamp` option (#323)
- Add `Session.run_always()`. (#331)

## 2020.5.24

- Add new options for `venv_backend`, including the ability to set the backend globally. (#326)
- Fix various typos in the documentation. (#325, #326, #281)
- Add `session.create_tmp`. (#320)
- Place all of Nox's command-line options into argparse groups. (#306)
- Add the `--pythons` command-line option to allow specifying which versions of Python to run. (#304)
- Add a significant amount of type annotations. (#297, #294, #290, #282, #274)
- Stop building universal wheels since we don't support Python 2. (#293)
- Add the ability to specify additional options for the virtualenv backend using `venv_params`. (#280)
- Prefer `importlib.metadata` for metadata loading, removing our dependency on `pkg_resources`. (#277)
- Add OmegaConf and Hydra to list of projects that use Nox. (#279)
- Use a more accurate error message, along with the cause, if loading of noxfile runs into error. (#272)
- Test against Python 3.8. (#270)
- Fix a syntax highlighting mistake in configuration docs. (#268)
- Use `stdout.isatty` to finalize color instead of `stdin.isatty`. (#267)

## 2019.11.9

- Fix example installation call for pip. (#259)
- Allow colorlog 4. (#257)
- Order Pythons in descending version in `appveyor.yml`. (#258)
- Add link to GitHub Action for Nox. (#255)
- Use double "\`" for inline code. (#254)
- Add types to `_option_set.py`. (#249)
- Add type hints to `tasks.py`. (#241)
- Fix typo (virtulenvs). (#247)
- Replace flake8 sorter with isort. (#242)
- Pass `VIRTUAL_ENV` environment variable to commands executed in a virtualenv. (#245)
- Fix docs to show correct list for parametrize. (#244)
- Add argcomplete dependency to conda test session. (#240)

## 2019.8.20

- Add `--verbose` for showing the output from all commands. (#174)
- Immediately exit if unknown arguments are passed. (#229)
- Document complex test_virtualenv fixtures. (#236)
- Resolve to interpreter 'python' in PATH if '--version' fits. (#224)
- Add shell autocomplete. (#228)
- Add `venv` as an option for `venv_backend`. (#231)
- Add gdbgui to list of projects. (#235)
- Add mypy to Nox's lint. (#230)
- Add pipx to projects that use nox. (#225)
- Add `session(venv_backend='conda')` option to use Conda environments. (#217, #221)
- Document how to call builtins on Windows. (#223)
- Replace `imp.load_source()` with `importlib`. (#214)
- Fix incorrect type in docstring & replace old-style format string. (#213)
- Allow specifying `stdout` and `stderr` to `session.run`.
- Add Salt to the list of projects that use Nox. (#209)
- Remove Python 2-specific code. (#203, #208)
- Grammar fixes. (#205, 206, 207)
- Update Nox's `noxfile.py` to use python3.7. (#204)

## 2019.5.30

- Add interactive property to session. (#196)
- Promote contributors to maintainers, add Open Collective details. (#201)
- Fix funding external link. (#200)
- Refactor how Nox defines and process options. (#187)
- Fix typo in tutorial. (#194)
- Use 'pytest' instead of 'py.test' in examples and configuration. (#193)
- Fix some CSS issues on mobile. (#192)
- Use short form of virtualenv path when creating the virtualenv. (#191)
- Refresh tutorial and fixup small docs things. (#190)
- Add the ability to give parametrized sessions a custom ID. (#186)
- Make --list list all available sessions, not just the selected ones. (#185)
- Allow providing a friendlier CLI name to sessions. (#170)
- Add urllib3 to the list of projects that use Nox (#182)
- Fix documentation link for Docker Cloud vs Hub (#179)

## 2019.4.11

- Include changelog in documentation. (#177)
- Use the relative path of the virtualenv in the "creating virtualenv" log message. (#176)
- Allow not passing "--upgrade" to `session.install` and change its default behavior to not upgrade. (#172)
- Expand environment variables when loading the noxfile from provided path. (#171)
- Add documentation around using Docker to run Nox. (#164)
- Don't colour output if `NO_COLOR` is set. (#163)
- Fix tox casing to be consistent with their docs, remove `.`` from pytest. (#160)
- Update issue templates.
- Add CODE_OF_CONDUCT.md.
- Add --install-only flag to install dependencies without running anything (#153)
- Fix function name in docs. (#155)
- Allow silent argument to be set in `session.install`. (#157)
- Run sessions in the same order specified on the command line. (#152)

## 2018.10.17

- Fix bug where empty parametrized sessions would fail. (#151)

## 2018.10.15

- Hide the python interpreter on sessions with only one. (#148)
-  Warn when programs not in the virtualenv are used, allow erroring and silencing the warning. (#147)
- Add --warn-on-external-run flag and the "external" keyword arg to session.run. (#147)
- Add nox.options which allows specifying command-line configuration in the Noxfile (#145)
- Add python_requires (>= 3.5) to setup.py.

## 2018.10.9

Breaking changes:

- Skip sessions with missing interpreters. Previously, missing interpreters would cause a failed session. Now they just cause a warning. The previous behavior can be used via `--error-on-missing-interpreters`. (#140)

New features:

- Add session.python property.

Other changes:

- Fix some warnings about escape sequences.
- Group command line args by usage for readability.
- Blacklist more Tox env vars in nox-to-tox.
- Documentation fixes, spelling, etc. (#134)
- Mention stickers in the contributors guide.
- Mention Invoke as a Nox alternative.


## 2018.9.14

- Check for ``NOXSESSION`` environment variable (#121)
- Fix typo in OpenCensus Python (#132)
- Add new documentation art created by Andrea Caprotti
- Add Python 3.7 to Travis CI (#129)

## 2018.8.28

Bugfixes:

* Adding `Session.__slots__`. (#128)
* Don't modify `Virtualenv.interpreter` in `_resolved_interpreter`. (#127)
* Fix tox-to-nox template.
* Add the ability to add descriptions to sessions. (#117)
* Using more specific regex in `_resolved_interpreter()`. (#119)

New features:

* Adding support for 32-bit binaries on Windows. (#100)

Internal/testing changes:

* Storing `platform.system()` as global in `nox.virtualenv`. (#124)
* Fix deploy script for Travis.
* Run docs on travis. (#122)
* Documentation style updates.

## 2018.8.23

**Heads up!** This is a very big release for Nox. Please read these release notes thoroughly and reach out to us on GitHub if you run into issues.

Breaking changes and other important notes:

* Nox is now published as "nox" on PyPI. This means that Nox is installed via `pip install nox` instead of `nox-automation`. Since the new release makes so many breaking changes, we won't be updating the old `nox-automation` package.
* Nox's configuration file is now called `noxfile.py` instead of `nox.py`.
* Nox no longer supports Python 2.7. You can still create and run Python 2.7 sessions, but Nox itself must be installed using Python 3.5+.
* Nox's behavior has been changed from *declarative*  to *imperative*. Session actions now run immediately. Existing code to setup session virtualenv, such as `session.interpreter` **will break**! Please consult the documentation on how to use `@nox.session(python=[...])` to configure virtualenvs for sessions.
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
