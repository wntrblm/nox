# Copyright 2016 Jon Wayne Parrott
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

from codecs import open

from setuptools import setup


long_description = open('README.rst', 'r', encoding='utf-8').read()


setup(
    name='nox-automation',

    version='0.17.0',

    description='Flexible test automation.',
    long_description=long_description,

    url='https://nox.readthedocs.org',

    author='Jon Wayne Parrott',
    author_email='jonwayne@google.com',

    license='Apache Software License',

    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',

        'License :: OSI Approved :: Apache Software License',

        'Topic :: Software Development :: Testing',
        'Environment :: Console',

        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',

        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Operating System :: Microsoft :: Windows'
    ],

    keywords='testing automation tox',

    packages=['nox'],

    include_package_data=True,

    install_requires=[
        'colorlog>=2.6.1,<3.0.0',
        'py>=1.4.0,<2.0.0',
        'six>=1.4.0,<2.0.0',
        'virtualenv>=14.0.0'],

    extras_require={
        'tox_to_nox': ['jinja2', 'tox']
    },

    entry_points={
        'console_scripts': [
            'nox=nox.main:main',
            'tox-to-nox=nox.tox_to_nox:main [tox_to_nox]'
        ],
    },
)
