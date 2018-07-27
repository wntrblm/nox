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

import nox


@nox.session()
def default(session):
    session.run('which', 'python')


@nox.session(python=['3.6', '3.7'])
def multi(session):
    session.run('which', 'python')
    session.install('markupsafe')
    session.log('Yay, imperative sessions!')


@nox.session(python=['3.6', '3.7'])
@nox.parametrize('meep', ['moop', 'boop'])
def multi_param(session, meep):
    session.run('which', 'python')
