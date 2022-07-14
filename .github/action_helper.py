from __future__ import annotations

import sys


def filter_version(version: str) -> str:
    """return python 'major.minor'"""

    # remove interpreter prefix
    if version.startswith("pypy-"):
        version_ = version[5:]
    elif version.startswith("pypy"):
        version_ = version[4:]
    else:
        version_ = version

    # remove extra specifier e.g. "3.11-dev" => "3.11"
    version_ = version_.split("-")[0]

    version_parts = version_.split(".")
    if len(version_parts) < 2:
        raise ValueError(f"invalid version: {version}")
    if not version_parts[0].isdigit():
        raise ValueError(f"invalid major python version: {version}")
    if not version_parts[1].isdigit():
        raise ValueError(f"invalid minor python version: {version}")
    return ".".join(version_parts[:2])


def setup_action(input_: str) -> None:
    versions = [version.strip() for version in input_.split(",") if version.strip()]

    pypy_versions = [version for version in versions if version.startswith("pypy")]
    pypy_versions_filtered = [filter_version(version) for version in pypy_versions]
    if len(pypy_versions) != len(set(pypy_versions_filtered)):
        raise ValueError(
            "multiple versions specified for the same 'major.minor' PyPy interpreter:"
            f" {pypy_versions}"
        )

    cpython_versions = [version for version in versions if version not in pypy_versions]
    cpython_versions_filtered = [
        filter_version(version) for version in cpython_versions
    ]
    if len(cpython_versions) != len(set(cpython_versions_filtered)):
        raise ValueError(
            "multiple versions specified for the same 'major.minor' CPython"
            f" interpreter: {cpython_versions}"
        )

    # cpython shall be installed last because
    # other interpreters also define pythonX.Y symlinks.
    versions = pypy_versions + cpython_versions

    # we want to install python 3.10 last to ease nox set-up
    if "3.10" in cpython_versions_filtered:
        index = cpython_versions_filtered.index("3.10")
        index = versions.index(cpython_versions[index])
        cpython_310 = versions.pop(index)
        versions.append(cpython_310)
    else:
        # add this to install nox
        versions.append("3.10")

    if len(versions) > 20:
        raise ValueError(f"too many interpreters to install: {len(versions)} > 20")

    print(f"::set-output name=interpreter_count::{len(versions)}")
    for i, version in enumerate(versions):
        print(f"::set-output name=interpreter_{i}::{version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise AssertionError(f"invalid arguments: {sys.argv}")
    setup_action(sys.argv[1])
