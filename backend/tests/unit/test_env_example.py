""".env.example matches the Settings defaults and the config contract (R4, FR-008)."""

import re
from pathlib import Path

import pytest

from app.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = REPO_ROOT / ".env.example"
CONFIGURATION_CONTRACT = (
    REPO_ROOT / "specs" / "001-walking-skeleton" / "contracts" / "configuration.md"
)
COMPOSE_ONLY_KEYS = {"BACKEND_PORT", "FRONTEND_PORT", "API_PROXY_TARGET"}
SETTINGS_KEYS = {name.upper() for name in Settings.model_fields}


def _example_keys() -> list[str]:
    lines = ENV_EXAMPLE.read_text().splitlines()
    return [line.split("=")[0] for line in lines if line and not line.startswith("#")]


def _contract_keys() -> list[str]:
    """Keys of the "Environment variables" table, in table order."""
    section = CONFIGURATION_CONTRACT.read_text().split("## Environment variables")[1]
    section = section.split("\n## ")[0]
    return re.findall(r"^\| `([A-Z_]+)` \|", section, flags=re.MULTILINE)


@pytest.fixture
def no_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop the conftest overrides so only the file and the defaults count."""
    monkeypatch.delenv("LLM_PROVIDER")
    monkeypatch.delenv("DATA_DIR")


def test_every_key_is_a_setting_or_compose_only() -> None:
    unknown = set(_example_keys()) - SETTINGS_KEYS - COMPOSE_ONLY_KEYS

    assert unknown == set()


def test_every_setting_is_in_the_file() -> None:
    missing = SETTINGS_KEYS - set(_example_keys())

    assert missing == set()


def test_keys_follow_the_contract_table_order() -> None:
    assert _example_keys() == _contract_keys()


def test_every_key_has_a_comment_line_above_it() -> None:
    lines = ENV_EXAMPLE.read_text().splitlines()
    uncommented = [
        line.split("=")[0]
        for index, line in enumerate(lines)
        if "=" in line
        and not line.startswith("#")
        and (index == 0 or not lines[index - 1].startswith("#"))
    ]

    assert uncommented == []


@pytest.mark.usefixtures("no_overrides")
def test_example_file_values_equal_the_built_in_defaults() -> None:
    from_file = Settings(_env_file=ENV_EXAMPLE).model_dump()
    defaults = Settings(_env_file=None).model_dump()

    assert from_file.pop("config_file_loaded") is True
    defaults.pop("config_file_loaded")
    assert from_file == defaults
