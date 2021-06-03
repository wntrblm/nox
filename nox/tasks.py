# Copyright 2017 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import importlib.machinery
import io
import json
import os
import types
from argparse import Namespace
from typing import List, Union

from colorlog.escape_codes import parse_colors

import nox
from nox import _options, registry
from nox._version import InvalidVersionSpecifier, VersionCheckFailed, check_nox_version
from nox.logger import logger
from nox.manifest import WARN_PYTHONS_IGNORED, Manifest
from nox.sessions import Result


def load_nox_module(global_config: Namespace) -> Union[types.ModuleType, int]:
    """Load the user's noxfile and return the module object for it.

    .. note::

        This task has two side effects; it makes ``global_config.noxfile``
        an absolute path, and changes the working directory of the process.

    Args:
        global_config (.nox.main.GlobalConfig): The global config.

    Returns:
        module: The module designated by the Noxfile path.
    """
    try:
        # Save the absolute path to the Noxfile.
        # This will inoculate it if nox changes paths because of an implicit
        # or explicit chdir (like the one below).
        global_config.noxfile = os.path.realpath(
            # Be sure to expand variables
            os.path.expandvars(global_config.noxfile)
        )

        # Check ``nox.needs_version`` by parsing the AST.
        check_nox_version(global_config.noxfile)

        # Move to the path where the Noxfile is.
        # This will ensure that the Noxfile's path is on sys.path, and that
        # import-time path resolutions work the way the Noxfile author would
        # guess.
        os.chdir(os.path.realpath(os.path.dirname(global_config.noxfile)))
        return importlib.machinery.SourceFileLoader(
            "user_nox_module", global_config.noxfile
        ).load_module()  # type: ignore

    except (VersionCheckFailed, InvalidVersionSpecifier) as error:
        logger.error(str(error))
        return 2
    except (IOError, OSError):
        logger.exception("Failed to load Noxfile {}".format(global_config.noxfile))
        return 2


def merge_noxfile_options(
    module: types.ModuleType, global_config: Namespace
) -> types.ModuleType:
    """Merges any modifications made to ``nox.options`` by the Noxfile module
    into global_config.

    Args:
        module (module): The Noxfile module.
        global_config (~nox.main.GlobalConfig): The global configuration.
    """
    _options.options.merge_namespaces(global_config, nox.options)
    return module


def discover_manifest(
    module: Union[types.ModuleType, int], global_config: Namespace
) -> Manifest:
    """Discover all session functions in the noxfile module.

    Args:
        module (module): The Noxfile module.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        ~.Manifest: A manifest of session functions.
    """
    # Find any function added to the session registry (meaning it was
    # decorated with @nox.session); do not sort these, as they are being
    # sorted by decorator call time.
    functions = registry.get()

    # Return the final dictionary of session functions.
    return Manifest(functions, global_config)


def filter_manifest(
    manifest: Manifest, global_config: Namespace
) -> Union[Manifest, int]:
    """Filter the manifest according to the provided configuration.

    Args:
        manifest (~.Manifest): The manifest of sessions to be run.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        Union[~.Manifest,int]: ``3`` if a specified session is not found,
            the manifest otherwise (to be sent to the next task).

    """
    # Filter by the name of any explicit sessions.
    # This can raise KeyError if a specified session does not exist;
    # log this if it happens.
    if global_config.sessions:
        try:
            manifest.filter_by_name(global_config.sessions)
        except KeyError as exc:
            logger.error("Error while collecting sessions.")
            logger.error(exc.args[0])
            return 3

    # Filter by python interpreter versions.
    # This function never errors, but may cause an empty list of sessions
    # (which is an error condition later).
    if global_config.pythons:
        manifest.filter_by_python_interpreter(global_config.pythons)

    # Filter by keywords.
    # This function never errors, but may cause an empty list of sessions
    # (which is an error condition later).
    if global_config.keywords:
        manifest.filter_by_keywords(global_config.keywords)

    # Return the modified manifest.
    return manifest


def honor_list_request(
    manifest: Manifest, global_config: Namespace
) -> Union[Manifest, int]:
    """If --list was passed, simply list the manifest and exit cleanly.

    Args:
        manifest (~.Manifest): The manifest of sessions to be run.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        Union[~.Manifest,int]: ``0`` if a listing is all that is requested,
            the manifest otherwise (to be sent to the next task).
    """
    if not global_config.list_sessions:
        return manifest

    # If the user just asked for a list of sessions, print that
    # and be done.

    print("Sessions defined in {noxfile}:\n".format(noxfile=global_config.noxfile))

    reset = parse_colors("reset") if global_config.color else ""
    selected_color = parse_colors("cyan") if global_config.color else ""
    skipped_color = parse_colors("white") if global_config.color else ""

    for session, selected in manifest.list_all_sessions():
        output = "{marker} {color}{session}{reset}"

        if selected:
            marker = "*"
            color = selected_color
        else:
            marker = "-"
            color = skipped_color

        if session.description is not None:
            output += " -> {description}"

        print(
            output.format(
                color=color,
                reset=reset,
                session=session.friendly_name,
                description=session.description,
                marker=marker,
            )
        )

    print(
        "\nsessions marked with {selected_color}*{reset} are selected, sessions marked with {skipped_color}-{reset} are skipped.".format(
            selected_color=selected_color, skipped_color=skipped_color, reset=reset
        )
    )
    return 0


def verify_manifest_nonempty(
    manifest: Manifest, global_config: Namespace
) -> Union[Manifest, int]:
    """Abort with an error code if the manifest is empty.

    Args:
        manifest (~.Manifest): The manifest of sessions to be run.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        Union[~.Manifest,int]: ``3`` on an empty manifest, the manifest
            otherwise.
    """
    if not manifest:
        return 3
    return manifest


def run_manifest(manifest: Manifest, global_config: Namespace) -> List[Result]:
    """Run the full manifest of sessions.

    Args:
        manifest (~.Manifest): The manifest of sessions to be run.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        tuple[~nox.sessions.Session,~.SessionStatus]: A two-tuple of the
            sessions and the result of each session that was run.
    """
    results = []

    # Iterate over each session in the manifest, and execute it.
    #
    # Note that it is possible for the manifest to be altered in any given
    # iteration.
    for session in manifest:
        # possibly raise warnings associated with this session
        if WARN_PYTHONS_IGNORED in session.func.should_warn:
            logger.warning(
                "Session {} is set to run with venv_backend='none', IGNORING its python={} parametrization. ".format(
                    session.name, session.func.should_warn[WARN_PYTHONS_IGNORED]
                )
            )

        result = session.execute()
        result.log(
            "Session {name} {status}.".format(
                name=session.friendly_name, status=result.imperfect
            )
        )
        results.append(result)

        # Sanity check: If we are supposed to stop on the first error case,
        # the abort now.
        if not result and global_config.stop_on_first_error:
            return results

    # The entire manifest has been processed; return the results.
    return results


def print_summary(results: List[Result], global_config: Namespace) -> List[Result]:
    """Print a summary of the results.

    Args:
        results (Sequence[~nox.sessions.Result]): A list of Result objects.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        results (Sequence[~nox.sessions.Result]): The results passed
            to this function, unmodified.
    """
    # Sanity check: Do not print results if there was only one session run.
    if len(results) <= 1:
        return results

    # Iterate over the results and print the result for each in a
    # human-readable way.
    logger.warning("Ran multiple sessions:")
    for result in results:
        result.log(
            "* {name}: {status}".format(
                name=result.session.friendly_name, status=result.status.name.lower()
            )
        )

    # Return the results that were sent to this function.
    return results


def create_report(results: List[Result], global_config: Namespace) -> List[Result]:
    """Write a report to the location designated in the config, if any.

    Args:
        results (Sequence[~nox.sessions.Result]): A list of Result objects
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        results (Sequence[~nox.sessions.Result]): The results passed
            to this function, unmodified.
    """
    # Sanity check: If no JSON report was requested, this is a no-op.
    if global_config.report is None:
        return results

    # Write the JSON report.
    with io.open(global_config.report, "w") as report_file:
        json.dump(
            {
                "result": int(all(results)),
                "sessions": [result.serialize() for result in results],
            },
            report_file,
            indent=2,
        )

    # Return back the results passed to this task.
    return results


def final_reduce(results: List[Result], global_config: Namespace) -> int:
    """Reduce the results to a final exit code.

    Args:
        results (Sequence[~nox.sessions.Result]): A list of Result objects
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        int: The final status code; ``0`` for success and ``1`` for failure.
    """
    if not all(results):
        return 1
    return 0
