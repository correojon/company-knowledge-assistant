"""Backend settings: environment variables, plus the repository-root ``.env``.

Defaults here are the single source of truth; ``.env.example`` must match them (R4).
"""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> repository root.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

DATABASE_FILENAME = "knowledge.sqlite3"


def _http_url(value: str) -> str:
    """Accept only http(s) URLs, but keep the text as written (no trailing slash)."""
    HttpUrl(value)
    return value


def _optional_http_url(value: str) -> str:
    return value if value == "" else _http_url(value)


class Settings(BaseSettings):
    # Reads no .env by itself; load_settings() passes the file explicitly. Compose-only
    # keys (BACKEND_PORT, ...) share the file, so unknown keys are ignored.
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    llm_provider: Literal["fake", "ollama", "openai_compat"] = "ollama"
    ollama_base_url: Annotated[str, AfterValidator(_http_url)] = (
        "http://localhost:11434"
    )
    ollama_model: str = "llama3.2:3b"
    openai_compat_base_url: Annotated[str, AfterValidator(_optional_http_url)] = ""
    openai_compat_api_key: SecretStr = SecretStr("")
    openai_compat_model: str = ""
    llm_timeout_seconds: float = Field(default=120, gt=0)
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    data_dir: Path = Path("./data")
    config_file_loaded: bool = False

    @property
    def database_path(self) -> Path:
        return self.data_dir / DATABASE_FILENAME


def load_settings() -> Settings:
    """Build settings, reading ``ENV_FILE`` only if it exists when called."""
    env_file = ENV_FILE if ENV_FILE.exists() else None
    return Settings(_env_file=env_file)


NO_CONFIG_NOTICE = (
    "Notice: no .env file found; using built-in defaults "
    "(copy .env.example to .env to customise)."
)


def startup_notice(settings: Settings) -> str | None:
    """The notice to print when no ``.env`` set the ``CONFIG_FILE_LOADED`` sentinel."""
    return None if settings.config_file_loaded else NO_CONFIG_NOTICE
