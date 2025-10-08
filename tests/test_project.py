import re

import pytest

from nox.project import dependency_groups, python_versions


def test_classifiers() -> None:
    pyproject = {
        "project": {
            "classifiers": [
                "Programming Language :: Python :: 3.7",
                "Programming Language :: Python :: 3.9",
                "Programming Language :: Python :: 3.12",
                "Programming Language :: Python",
                "Programming Language :: Python :: 3 :: Only",
                "Topic :: Software Development :: Testing",
            ],
            "requires-python": ">=3.10",
        }
    }

    assert python_versions(pyproject) == ["3.7", "3.9", "3.12"]


def test_no_classifiers() -> None:
    pyproject = {"project": {"requires-python": ">=3.9"}}
    with pytest.raises(ValueError, match="No Python version classifiers"):
        python_versions(pyproject)


def test_no_requires_python() -> None:
    pyproject = {"project": {"classifiers": ["Programming Language :: Python :: 3.12"]}}
    with pytest.raises(
        ValueError, match=re.escape('No "project.requires-python" value set')
    ):
        python_versions(pyproject, max_version="3.13")


def test_python_range() -> None:
    pyproject = {
        "project": {
            "classifiers": [
                "Programming Language :: Python :: 3.7",
                "Programming Language :: Python :: 3.9",
                "Programming Language :: Python :: 3.12",
                "Programming Language :: Python",
                "Programming Language :: Python :: 3 :: Only",
                "Topic :: Software Development :: Testing",
            ],
            "requires-python": ">=3.10",
        }
    }

    assert python_versions(pyproject, max_version="3.12") == ["3.10", "3.11", "3.12"]
    assert python_versions(pyproject, max_version="3.11") == ["3.10", "3.11"]


def test_python_range_gt() -> None:
    pyproject = {"project": {"requires-python": ">3.2.1,<3.3"}}

    assert python_versions(pyproject, max_version="3.4") == ["3.2", "3.3", "3.4"]


def test_python_range_no_min() -> None:
    pyproject = {"project": {"requires-python": "==3.3.1"}}

    with pytest.raises(ValueError, match="No minimum version found"):
        python_versions(pyproject, max_version="3.5")


def test_dependency_groups() -> None:
    example = {
        "dependency-groups": {
            "test": ["pytest", "coverage"],
            "docs": ["sphinx", "sphinx-rtd-theme"],
            "typing": ["mypy", "types-requests"],
            "typing-test": [
                {"include-group": "typing"},
                {"include-group": "test"},
                "useful-types",
            ],
        }
    }

    assert dependency_groups(example, "test") == ("pytest", "coverage")
    assert dependency_groups(example, "typing-test") == (
        "mypy",
        "types-requests",
        "pytest",
        "coverage",
        "useful-types",
    )
    assert dependency_groups(example, "typing_test") == (
        "mypy",
        "types-requests",
        "pytest",
        "coverage",
        "useful-types",
    )
