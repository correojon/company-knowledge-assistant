"""build_provider maps validated settings to a provider class (contract rule 5)."""

import pytest

from app.config import Settings
from app.llm.factory import build_provider
from app.llm.fake import FakeProvider
from app.llm.ollama import OllamaProvider


def test_fake_gives_a_fake_provider() -> None:
    provider = build_provider(Settings(llm_provider="fake"))

    assert isinstance(provider, FakeProvider)
    assert provider.model == "fake"


def test_ollama_gives_an_ollama_provider_from_settings() -> None:
    settings = Settings(
        llm_provider="ollama",
        ollama_base_url="http://ollama.test:11434",
        ollama_model="mistral:7b",
        llm_timeout_seconds=42,
    )

    provider = build_provider(settings)

    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "http://ollama.test:11434"
    assert provider.model == "mistral:7b"
    assert provider.timeout_seconds == 42


def test_ollama_is_built_without_contacting_the_server() -> None:
    # The network guard turns any connection attempt into a test failure.
    build_provider(Settings(llm_provider="ollama", ollama_base_url="http://nowhere:1"))


def test_openai_compat_is_not_mapped_yet() -> None:
    with pytest.raises(NotImplementedError, match="T032"):
        build_provider(Settings(llm_provider="openai_compat"))
