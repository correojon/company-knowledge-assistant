"""Pick the configured provider (contracts/llm-provider.md, rule 5)."""

from app.config import Settings
from app.llm.base import LLMProvider
from app.llm.fake import FakeProvider
from app.llm.ollama import OllamaProvider


def build_provider(settings: Settings) -> LLMProvider:
    """Map an already-validated ``llm_provider`` to its class.

    Performs no I/O: reachability is reported later by ``check()``.
    """
    match settings.llm_provider:
        case "fake":
            return FakeProvider()
        case "ollama":
            return OllamaProvider(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                timeout_seconds=settings.llm_timeout_seconds,
            )
        case "openai_compat":
            raise NotImplementedError("the openai_compat provider arrives in T032")
