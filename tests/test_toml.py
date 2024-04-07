import textwrap
from pathlib import Path

import pytest

import nox


def test_load_pyproject(tmp_path: Path) -> None:
    filepath = tmp_path / "example.toml"
    filepath.write_text(
        """
        [project]
        name = "hi"
        version = "1.0"
        dependencies = ["numpy", "requests"]
        """
    )

    toml = nox.toml.load(filepath)
    assert toml["project"]["dependencies"] == ["numpy", "requests"]


@pytest.mark.parametrize("example", ["example.py", "example"])
def test_load_script_block(tmp_path: Path, example: str) -> None:
    filepath = tmp_path / example
    filepath.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env pipx run
            # /// script
            # requires-python = ">=3.11"
            # dependencies = [
            #   "requests<3",
            #   "rich",
            # ]
            # ///

            import requests
            from rich.pretty import pprint

            resp = requests.get("https://peps.python.org/api/peps.json")
            data = resp.json()
            pprint([(k, v["title"]) for k, v in data.items()][:10])
            """
        )
    )

    toml = nox.toml.load(filepath)
    assert toml["dependencies"] == ["requests<3", "rich"]


def test_load_no_script_block(tmp_path: Path) -> None:
    filepath = tmp_path / "example.py"
    filepath.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/python

            import requests
            from rich.pretty import pprint

            resp = requests.get("https://peps.python.org/api/peps.json")
            data = resp.json()
            pprint([(k, v["title"]) for k, v in data.items()][:10])
            """
        )
    )

    with pytest.raises(ValueError, match="No script block found"):
        nox.toml.load(filepath)


def test_load_multiple_script_block(tmp_path: Path) -> None:
    filepath = tmp_path / "example.py"
    filepath.write_text(
        textwrap.dedent(
            """\
            # /// script
            # dependencies = [
            #   "requests<3",
            #   "rich",
            # ]
            # ///

            # /// script
            # requires-python = ">=3.11"
            # ///

            import requests
            from rich.pretty import pprint

            resp = requests.get("https://peps.python.org/api/peps.json")
            data = resp.json()
            pprint([(k, v["title"]) for k, v in data.items()][:10])
            """
        )
    )

    with pytest.raises(ValueError, match="Multiple script blocks found"):
        nox.toml.load(filepath)


def test_load_non_recongnised_extension():
    msg = "Extension must be .py or .toml, got .txt"
    with pytest.raises(ValueError, match=msg):
        nox.toml.load("some.txt")
