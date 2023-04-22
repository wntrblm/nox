# Changelog

## 2023.04.22

We'd like to thank the following folks who contributed to this release:
- @crwilcox 
- @dcermak 
- @edgarrmondragon 
- @FollowTheProcess 
- @henryiii 
- @reaperhulk 
- @scop 

New Features:
* Add support for `NOXPYTHON`, `NOXEXTRAPYTHON` and `NOXFORCEPYTHON` by @edgarrmondragon in https://github.com/wntrblm/nox/pull/688
* feat: --json --list-sessions by @henryiii in https://github.com/wntrblm/nox/pull/665

Documentation Improvements:
* style: spelling and grammar fixes by @scop in https://github.com/wntrblm/nox/pull/682
* Add invite link to the discord server to CONTRIBUTING.md by @dcermak in https://github.com/wntrblm/nox/pull/679

Internal Changes:
* chore: update pre-commit hooks by @edgarrmondragon in https://github.com/wntrblm/nox/pull/690
* chore: move to using Ruff by @henryiii in https://github.com/wntrblm/nox/pull/691
* Fix assertion in GHA tests by @FollowTheProcess in https://github.com/wntrblm/nox/pull/670
* ci: some minor fixes by @henryiii in https://github.com/wntrblm/nox/pull/675
* Constrain tox to <4.0.0 and minor fixes by @FollowTheProcess in https://github.com/wntrblm/nox/pull/677
* chore: long term fix for bugbear opinionated checks by @henryiii in https://github.com/wntrblm/nox/pull/678
* chore: switch to hatchling by @henryiii in https://github.com/wntrblm/nox/pull/659
* Don't run python 2.7 virtualenv tests for newer versions of virtualenv by @crwilcox in https://github.com/wntrblm/nox/pull/702
* allow the use of argcomplete 3 by @reaperhulk in https://github.com/wntrblm/nox/pull/700
* fix: enable `list_sessions` for session completion by @scop in https://github.com/wntrblm/nox/pull/699
* chore: remove 3.6 tests, min version is 3.7 by @crwilcox in https://github.com/wntrblm/nox/pull/703


## 2022.11.21

We'd like to thank the following folks who contributed to this release:
- @airtower-luna
- @DiddiLeija
- @FollowTheProcess
- @henryiii
- @hynek
- @Julian
- @nhtsai
- @paw-lu

New features:
- Include Python 3.11 classifier & testing (#655)

Improvements:
- Fixed a few typos (#661, #660)
- Drop dependency on `py` (#647)
- `nox.session.run` now accepts a `pathlib.Path` for the command (#649)
- Document `nox.session.run`'s `stdout` and `stderr` arguments and add example of capturing output (#651)

Bugfixes:
- GitHub Action: replace deprecated set-output command (#668)
- GitHub Action: point docs to 2022.8.7 not latest (#664)
- Docs: fix argument passing in `session.posargs` example (#653)
- Include GitHub action helper in `MANIFEST.in` (#645)

Internal changes:
- GitHub Action: move to 3.11 final (#667)
- Cleanup Python 2 style code (#657)
- Update tools used in pre-commit (#646, #656)


## 2022.8.7

We'd like to thank the following folks who contributed to this release:
- @CN-M
- @crwilcox
- @DiddiLeija
- @edgarrmondragon
- @FollowTheProcess
- @hauntsaninja
- @henryiii
- @johnthagen
- @jwodder
- @ktbarrett
- @mayeut
- @meowmeowmeowcat
- @NickleDave
- @raddessi
- @zhanpon

Removals:
- Drop support for Python 3.6 (#526)
- Disable running `session.install` outside a venv (#580)

New features:
- Official Nox GitHub Action (#594, #606, #609, #620, #629, #637, #632, #633)
- Missing interpreters now error the session on CI by default (#567)
- Allow configurable child shutdown timeouts (#565)
- Add session tags (#627)
- Add short `-N` alias for `--no-reuse-existing-virtualenvs` (#639)
- Export session name in `NOX_CURRENT_SESSION` environment variable (#641)

Improvements:
- Add `VENV_DIR` to `dev` session in cookbook (#591)
- Fix typo in `tutorial.rst` (#586)
- Use consistent spelling for Nox in documentation (#581)
- Support descriptions in `tox-to-nox` (#575)
- Document that `silent=True` returns the command output (#578)
- Support argcomplete v2 (#564)

Bugfixes:
-  Fix incorrect `FileNotFoundError` in `load_nox_module` (#571)

Internal changes:
- Update the classifiers, documentation, and more to point to the new Winterbloom location (#587)
- Support PEP 621 (`pyproject.toml`) (#616, #619)
- Configure language code to avoid warning on sphinx build (#626)
- Use latest GitHub action runners and include macOS (#613)
- Jazz up the README with some badges/logo etc. (#605, #614)
- Prefer type checking against Jinja2 (#610)
- Introduce GitHub issue forms (#600, #603, #608)
- Full strictness checking on mypy (#595, #596)
- Drop 99% coverage threshold flag for 3.10 in noxfile (#593)
- Create a `requirements-dev.txt` (#582)
- Use `myst-parser` for Markdown docs (#561)

## 2022.1.7

Claudio Jolowicz, Diego Ramirez, and Tom Fleet have become maintainers of Nox. We'd like to thank the following folks who contributed to this release:

- @brettcannon
- @cjolowicz
- @dhermes
- @DiddiLeija
- @FollowTheProcess
- @franekmagiera
- @henryiii
- @jugmac00
- @maciej-lech
- @nawatts
- @Tolker-KU

New features:
- Add `mamba` backend (#444, #448, #546, #551)
- Add `session.debug` to show debug-level messages (#489)
- Add cookbook page to the documentation (#483)
- Add support for the `FORCE_COLOR` environment variable (#524, #548)
- Allow using `session.chdir()` as a context manager (#543)
- Deprecate use of `session.install()` without a valid backend (#537)

Improvements:
- Test against Python 3.10 (#495, #502, #506)
- Add support for the `channel` option when using the `conda` backend (#522)
- Show more specific error message when the `--keywords` expression contains a syntax error (#493)
- Include reference to `session.notify()` in tutorial page (#500)
- Document how `session.run()` fails and how to handle failures  (#533)
- Allow the list of sessions to be empty (#523)

Bugfixes:
- Fix broken temporary directory when using `session.chdir()` (#555, #556)
- Set the `CONDA_PREFIX` environment variable (#538)
- Fix `bin` directory for the `conda` backend on Windows (#535)

Internal changes:
- Replace deprecated `load_module` with `exec_module` (#498)
- Include tests with source distributions (#552)
- Add missing copyright notices (#509)
- Use the new ReadTheDocs configurations (#527)
- Bump the Python version used by ReadTheDocs to 3.8 (#496)
- Improve the Sphinx config file (#499)
- Update all linter versions (#528)
- Add pre-commit and new checks (#530, #539)
- Check `MANIFEST.in` during CI (#552)
- Remove redundant `LICENSE` from `MANIFEST.in` (#505)
- Make `setuptools` use the standard library's `distutils` to work around `virtualenv` bug. (#547, #549)
- Use `shlex.join()` when logging a command (#490)
- Use `shutil.rmtree()` over shelling out to `rm -rf` in noxfile (#519)
- Fix missing Python 3.9 CI session (#529)
- Unpin docs session and add `--error-on-missing-interpreter` to CI (#532)
- Enable color output from Nox, pytest, and pre-commit during CI (#542)
- Only run `conda_tests` session by default if user has conda installed (#521)
- Update dependencies in `requirements-conda-test.txt` (#536)


## 2021.10.1

New features:
- Add `session.warn` to output warnings (#482)
- Add a shared session cache directory (#476)
- Add `session.invoked_from` (#472)

Improvements:
- Conda logs now respect `nox.options.verbose` (#466)
- Add `session.notify` example to docs (#467)
- Add friendlier message if no `noxfile.py` is found (#463)
- Show the `noxfile.py` docstring when using `nox -l` (#459)
- Mention more projects that use Nox in the docs (#460)

Internal changes:
- Move configs into pyproject.toml or setup.cfg (flake8) (#484)
- Decouple `test_session_completer` from project level noxfile (#480)
- Run Flynt to convert str.format to f-strings (#464)
- Add python 3.10.0-rc2 to GitHub Actions (#475, #479)
- Simplify CI build (#461)
- Use PEP 517 build system, remove `setup.py`, use `setup.cfg` (#456, #457, #458)
- Upgrade to mypy 0.902 (#455)

Special thanks to our contributors:
- @henryiii
- @cjolowicz
- @FollowTheProcess
- @franekmagiera
- @DiddiLeija

## 2021.6.12

- Fix crash on Python 2 when reusing environments. (#450)
- Hide staleness check behind a feature flag. (#451)
- Group command-line options in `--help` message by function. (#442)
- Avoid polluting tests with a .nox directory. (#445)

## 2021.6.6

- Add option `--no-install` to skip install commands in reused environments. (#432)
- Add option `--force-python` as shorthand for `--python` and `--extra-python`. (#427)
- Do not reuse environments if the interpreter or the environment type has changed. (#418, #425, #428)
- Allow common variations in session names with parameters, such as double quotes instead of single quotes. Session names are considered equal if they produce the same Python AST. (#417, #434)
- Preserve the order of parameters in session names. (#401)
- Allow `@nox.parametrize` to select the session Python. (#413)
- Allow passing `posargs` when scheduling another session via `session.notify`. (#397)
- Prevent sessions from modifying each other's posargs. (#439)
- Add `nox.needs_version` to specify Nox version requirements. (#388)
- Add `session.name` to get the session name. (#386)
- Gracefully shutdown child processes. (#393)
- Decode command output using the system locale if UTF-8 decoding fails. (#380)
- Fix creation of Conda environments when `venv_params` is used. (#420)
- Various improvements to Nox's type annotations. (#376, #377, #378)
- Remove outdated notes on Windows compatibility from the documentation. (#382)
- Increase Nox's test coverage on Windows. (#300)
- Avoid mypy searching for configuration files in other directories. (#402)
- Replace AppVeyor and Travis CI by GitHub Actions. (#389, #390, #403)
- Allow colorlog <7.0.0. (#431)
- Drop contexter from test requirements. (#426)
- Upgrade linters to the latest version. (#438)

## 2020.12.31

- Fix `NoxColoredFormatter.format` (#374)
- Use conda remove to clean up existing conda environments (#373)
- Support users specifying an undeclared parametrization of python via `--extra-python` (#361)
- Support double-digit minor version in `python` keyword (#367)
- Add `py.typed` to `manifest.in` (#360)
- Update Nox to latest supported python versions. (#362)
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
- Add pipx to projects that use Nox. (#225)
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

* Fix Nox not returning a non-zero exit code on failure. (#55)
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
