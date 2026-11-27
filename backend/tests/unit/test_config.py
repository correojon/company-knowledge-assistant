"""Settings defaults, field validation, secret redaction and .env loading (R4, R5)."""

import importlib.util
from pathlib import Path

import pytest
from pydantic import ValidationError

from app import config
from app.config import Settings, load_settings


@pytest.fixture
def no_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop the conftest overrides so every field falls back to its default."""
    monkeypatch.delenv("LLM_PROVIDER")
    monkeypatch.delenv("DATA_DIR")


@pytest.mark.usefixtures("no_overrides")
def test_defaults_match_data_model() -> None:
    settings = Settings()

    assert settings.llm_provider == "ollama"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "llama3.2:3b"
    assert settings.openai_compat_base_url == ""
    assert settings.openai_compat_api_key.get_secret_value() == ""
    assert settings.openai_compat_model == ""
    assert settings.llm_timeout_seconds == 120
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.data_dir == Path("./data")
    assert settings.config_file_loaded is False


def test_database_path_is_inside_data_dir(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "store")

    assert settings.database_path == tmp_path / "store" / "knowledge.sqlite3"


def test_environment_variables_override_defaults(tmp_path: Path) -> None:
    settings = Settings()

    assert settings.llm_provider == "fake"
    assert settings.data_dir == tmp_path / "data"


@pytest.mark.parametrize("value", ["", "banana"])
def test_llm_provider_rejects_unknown_values(value: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        Settings(llm_provider=value)

    assert excinfo.value.errors()[0]["loc"] == ("llm_provider",)


@pytest.mark.parametrize("field", ["ollama_base_url", "openai_compat_base_url"])
@pytest.mark.parametrize("value", ["ftp://x", "not a url"])
def test_base_urls_reject_non_http_values(field: str, value: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        Settings(**{field: value})

    assert excinfo.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("field", ["ollama_base_url", "openai_compat_base_url"])
def test_base_urls_are_kept_as_written(field: str) -> None:
    settings = Settings(**{field: "https://api.example.com/openai/v1"})

    assert getattr(settings, field) == "https://api.example.com/openai/v1"


def test_ollama_base_url_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        Settings(ollama_base_url="")


@pytest.mark.parametrize("value", [0, -1])
def test_llm_timeout_must_be_positive(value: float) -> None:
    with pytest.raises(ValidationError) as excinfo:
        Settings(llm_timeout_seconds=value)

    assert excinfo.value.errors()[0]["loc"] == ("llm_timeout_seconds",)


def test_api_key_is_never_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-test-SECRET123")
    settings = Settings()

    assert settings.openai_compat_api_key.get_secret_value() == "sk-test-SECRET123"
    assert "SECRET123" not in repr(settings)
    assert "SECRET123" not in str(settings)
    assert "SECRET123" not in settings.model_dump_json()


def test_load_settings_reads_env_file_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CONFIG_FILE_LOADED=true\n"
        "OLLAMA_MODEL=model-from-dotenv\n"
        # Compose-only keys live in the same file and must not be rejected.
        "BACKEND_PORT=8000\n"
    )
    monkeypatch.setattr(config, "ENV_FILE", env_file)

    settings = load_settings()

    assert settings.config_file_loaded is True
    assert settings.ollama_model == "model-from-dotenv"


def test_environment_wins_over_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_PROVIDER=ollama\n")
    monkeypatch.setattr(config, "ENV_FILE", env_file)

    assert load_settings().llm_provider == "fake"


def test_load_settings_ignores_missing_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "absent" / ".env")

    settings = load_settings()

    assert settings.config_file_loaded is False
    assert settings.ollama_model == "llama3.2:3b"


def test_plain_settings_never_read_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OLLAMA_MODEL=model-from-dotenv\n")
    monkeypatch.setattr(config, "ENV_FILE", env_file)

    assert Settings().ollama_model == "llama3.2:3b"


def test_env_file_is_the_repository_root_dotenv() -> None:
    # conftest.py patches app.config.ENV_FILE, so load an unpatched copy of the module.
    spec = importlib.util.spec_from_file_location("_config_copy", config.__file__)
    assert spec is not None and spec.loader is not None
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    backend_dir = Path(__file__).resolve().parents[2]

    assert backend_dir.name == "backend"
    assert fresh.ENV_FILE == backend_dir.parent / ".env"


def test_tests_never_see_the_real_env_file() -> None:
    assert not config.ENV_FILE.exists()
