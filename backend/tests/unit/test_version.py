"""The reported version comes from one place: backend/pyproject.toml."""

import tomllib
from pathlib import Path

import app

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_matches_pyproject() -> None:
    with PYPROJECT.open("rb") as f:
        project_version = tomllib.load(f)["project"]["version"]

    assert app.__version__ == project_version
