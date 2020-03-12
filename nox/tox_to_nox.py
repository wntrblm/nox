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

"""Naively converts tox.ini files into noxfile.py files."""

import argparse
import io
import pkgutil
from typing import Any, Iterator

import jinja2
import tox.config

_TEMPLATE = jinja2.Template(
    pkgutil.get_data(__name__, "tox_to_nox.jinja2").decode("utf-8"),  # type: ignore
    extensions=["jinja2.ext.do"],
)


def wrapjoin(seq: Iterator[Any]) -> str:
    return ", ".join(["'{}'".format(item) for item in seq])


def main() -> None:
    parser = argparse.ArgumentParser(description="Converts toxfiles to noxfiles.")
    parser.add_argument("--output", default="noxfile.py")

    args = parser.parse_args()

    config = tox.config.parseconfig([])
    output = _TEMPLATE.render(config=config, wrapjoin=wrapjoin)

    with io.open(args.output, "w") as outfile:
        outfile.write(output)
