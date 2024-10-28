import pytest

from nox.project import python_list


def test_classifiers():
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

    assert python_list(pyproject) == ["3.7", "3.9", "3.12"]


def test_no_classifiers():
    pyproject = {"project": {"requires-python": ">=3.9"}}
    with pytest.raises(ValueError, match="No Python version classifiers"):
        python_list(pyproject)


def test_no_requires_python():
    pyproject = {"project": {"classifiers": ["Programming Language :: Python :: 3.12"]}}
    with pytest.raises(ValueError, match='No "project.requires-python" value set'):
        python_list(pyproject, max_version="3.13")


def test_python_range():
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

    assert python_list(pyproject, max_version="3.12") == ["3.10", "3.11", "3.12"]
    assert python_list(pyproject, max_version="3.11") == ["3.10", "3.11"]


def test_python_range_gt():
    pyproject = {"project": {"requires-python": ">3.2.1,<3.3"}}

    assert python_list(pyproject, max_version="3.4") == ["3.2", "3.3", "3.4"]


def test_python_range_no_min():
    pyproject = {"project": {"requires-python": "==3.3.1"}}

    with pytest.raises(ValueError, match="No minimum version found"):
        python_list(pyproject, max_version="3.5")
