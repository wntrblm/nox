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

from codecs import open

from setuptools import setup

long_description = open("README.rst", "r", encoding="utf-8").read()

setup(
    name="nox",
    version="2021.6.12",
    description="Flexible test automation.",
    long_description=long_description,
    url="https://nox.thea.codes",
    author="Alethea Katherine Flowers",
    author_email="me@thea.codes",
    license="Apache Software License",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Testing",
        "Environment :: Console",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: Unix",
        "Operating System :: Microsoft :: Windows",
    ],
    keywords="testing automation tox",
    packages=["nox"],
    package_data={"nox": ["py.typed"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "argcomplete>=1.9.4,<2.0",
        "colorlog>=2.6.1,<7.0.0",
        "packaging>=20.9",
        "py>=1.4.0,<2.0.0",
        "virtualenv>=14.0.0",
        "importlib_metadata; python_version < '3.8'",
    ],
    extras_require={"tox_to_nox": ["jinja2", "tox"]},
    entry_points={
        "console_scripts": [
            "nox=nox.__main__:main",
            "tox-to-nox=nox.tox_to_nox:main [tox_to_nox]",
        ]
    },
    project_urls={
        "Documentation": "https://nox.thea.codes",
        "Source Code": "https://github.com/theacodes/nox",
        "Bug Tracker": "https://github.com/theacodes/nox/issues",
    },
    python_requires=">=3.6",
)
