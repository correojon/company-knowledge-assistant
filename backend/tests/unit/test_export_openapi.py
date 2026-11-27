"""OpenAPI export for the frontend's generated types (R10, FR-016)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app import config

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "export_openapi.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("export_openapi", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_is_stable_sorted_and_contains_health_report(tmp_path: Path) -> None:
    export_openapi = _load_script()
    first, second = tmp_path / "a.json", tmp_path / "b.json"

    export_openapi.main([str(first)])
    export_openapi.main([str(second)])

    text = first.read_text(encoding="utf-8")
    assert first.read_bytes() == second.read_bytes()
    assert text.endswith("\n")
    schema = json.loads(text)
    assert text == json.dumps(schema, indent=2, sort_keys=True) + "\n"
    assert "HealthReport" in schema["components"]["schemas"]


def test_export_ignores_local_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_PROVIDER=banana\n", encoding="utf-8")
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    monkeypatch.delenv("LLM_PROVIDER")
    output = tmp_path / "openapi.json"

    _load_script().main([str(output)])

    assert "HealthReport" in json.loads(output.read_text())["components"]["schemas"]


def test_default_output_is_the_frontend_api_folder() -> None:
    export_openapi = _load_script()

    repo_root = Path(__file__).resolve().parents[3]
    assert export_openapi.DEFAULT_OUTPUT == (
        repo_root / "frontend" / "src" / "api" / "openapi.json"
    )
