# Copyright 2016 Alethea Katherine Flowers
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

"""The Nox `main` function and helpers."""

from __future__ import annotations

import sys
from typing import Any

from nox import _options, tasks, workflow
from nox._version import get_nox_version
from nox.logger import setup_logging

__all__ = ["execute_workflow", "main"]


def __dir__() -> list[str]:
    return __all__


def execute_workflow(args: Any) -> int:
    """
    Execute the appropriate tasks.
    """

    return workflow.execute(
        global_config=args,
        workflow=(
            tasks.load_nox_module,
            tasks.merge_noxfile_options,
            tasks.discover_manifest,
            tasks.filter_manifest,
            tasks.honor_list_request,
            tasks.run_manifest,
            tasks.print_summary,
            tasks.create_report,
            tasks.final_reduce,
        ),
    )


def main() -> None:
    args = _options.options.parse_args()

    if args.help:
        _options.options.print_help()
        return

    if args.version:
        print(get_nox_version(), file=sys.stderr)
        return

    setup_logging(
        color=args.color, verbose=args.verbose, add_timestamp=args.add_timestamp
    )

    exit_code = execute_workflow(args)

    # Done; exit.
    sys.exit(exit_code)
