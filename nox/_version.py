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

from distutils.version import LooseVersion
from os import path
from re import compile

from pkg_resources import get_distribution

from nox.logger import logger


def nox_version():
    # obtain version of the currently running nox instance
    dist = get_distribution("nox")
    return LooseVersion(dist.version)


def parse_needs_nox(noxfile):
    if not path.exists(noxfile):
        return None

    # find a "needs_nox" line and parse the version
    regex = compile(r"""^needs_nox\s*=\s*(['"])(?P<version>[^\1]*)\1.*$""")
    with open(noxfile, "r") as noxfile:
        for line in noxfile:
            m = regex.match(line)
            if m:
                needs_version = LooseVersion(m.group("version"))
                return needs_version


def needs_nox(noxfile, noxfile_module=None):
    needed = None
    if not noxfile_module:
        needed = parse_needs_nox(noxfile)
    elif hasattr(noxfile_module, "needs_nox"):
        needed = LooseVersion(noxfile_module.needs_nox)
    return needed


def is_version_sufficient(noxfile, needed_version):
    if needed_version and needed_version > nox_version():
        logger.error(
            "Noxfile {} needs at least Nox {} and therefore it cannot be used "
            "with this version.".format(noxfile, str(needed_version))
        )
        return False
    return True
