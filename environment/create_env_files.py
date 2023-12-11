import logging
import os
import sys
from pathlib import Path

PYTHON_VERSIONS = ["3.7", "3.8", "3.9", "3.10", "3.11"]
LOCK_VERSIONS = ["3.11"]


logger = logging.getLogger(__name__)


HERE = Path(__file__).resolve().parent


def create_yaml(*deps: str) -> str:
    x = ["dependencies:"]
    x.extend([f"  - {dep}" for dep in deps])
    return "\n".join(x) + "\n"


def create_yaml_files():
    os.chdir(HERE)
    logging.info(f"cwd: {Path.cwd()}")

    # load requirements:
    requirements = [
        x.replace(" ", "")
        for x in Path("../requirements-conda-test.txt").read_text().strip().split("\n")
    ]

    # create environment files
    for py in PYTHON_VERSIONS:
        yaml = Path(f"py{py}-conda-test.yaml")

        # make sure these have python and pip
        s = create_yaml(f"python={py}", *requirements, "pip")
        with yaml.open("w") as f:
            f.write(s)


def create_lock_files():
    import subprocess

    os.chdir(HERE)
    for py in LOCK_VERSIONS:
        subprocess.run(
            [
                "conda-lock",
                "lock",
                "-c",
                "conda-forge",
                f"--file=py{py}-conda-test.yaml",
                f"--lockfile=py{py}-conda-test-conda-lock.yml",
            ],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print("pass yaml (to create yaml files) or lock (to create lock files)")

    else:
        for arg in args:
            if arg == "yaml":
                create_yaml_files()
            elif arg == "lock":
                create_lock_files()
