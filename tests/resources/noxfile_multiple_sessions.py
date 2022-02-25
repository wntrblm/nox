# Copyright 2018 Alethea Katherine Flowers
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

from __future__ import annotations

import nox

# Deliberately giving these silly names so we know this is not confused
# with the projects Noxfile


@nox.session
def testytest(session):
    session.log("Testing")


@nox.session
def lintylint(session):
    session.log("Linting")


@nox.session
def typeytype(session):
    session.log("Type Checking")
