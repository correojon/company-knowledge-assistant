"""GET /api/health reports backend, store and LLM status.

Contract: contracts/openapi-health.yaml.

Every test runs in-process through ``TestClient``; the Ollama case uses
``httpx.MockTransport``, so nothing leaves the process.
"""

from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app
from app.llm.ollama import OllamaProvider

AppFactory = Callable[..., FastAPI]

OLLAMA_URL = "http://ollama.test:11434"


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None, value
    assert parsed.utcoffset() == UTC.utcoffset(None), value
    return parsed


def test_health_ok_with_fake_provider(app_factory: AppFactory) -> None:
    with TestClient(app_factory()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "version", "database", "llm"}
    assert body["status"] == "ok"
    assert body["version"] == app.__version__

    assert body["database"] == {
        "status": "ok",
        "schema_revision": "0001_baseline",
        "vector_search": "ok",
        "vector_search_version": body["database"]["vector_search_version"],
    }
    assert body["database"]["vector_search_version"]

    llm = body["llm"]
    assert set(llm) == {"provider", "model", "status", "reason", "checked_at"}
    assert llm["provider"] == "fake"
    assert llm["model"] == "fake"
    assert llm["status"] == "available"
    assert llm["reason"] is None
    _parse_utc(llm["checked_at"])


def test_llm_unavailable_keeps_backend_ok(app_factory: AppFactory) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = OllamaProvider(
        OLLAMA_URL, "llama3.2:3b", 120, transport=httpx.MockTransport(refuse)
    )

    with TestClient(app_factory(provider=provider)) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["status"] == "ok"
    llm = body["llm"]
    assert llm["provider"] == "ollama"
    assert llm["model"] == "llama3.2:3b"
    assert llm["status"] == "unavailable"
    assert llm["reason"] == f"cannot reach {OLLAMA_URL} (is Ollama running?)"
    _parse_utc(llm["checked_at"])


def test_health_cached_within_60s(app_factory: AppFactory) -> None:
    probes: list[httpx.Request] = []

    def tags(request: httpx.Request) -> httpx.Response:
        probes.append(request)
        return httpx.Response(200, json={"models": [{"name": "llama3.2:3b"}]})

    provider = OllamaProvider(
        OLLAMA_URL, "llama3.2:3b", 120, transport=httpx.MockTransport(tags)
    )

    with TestClient(app_factory(provider=provider)) as client:
        first = client.get("/api/health").json()
        second = client.get("/api/health").json()

    assert len(probes) == 1
    assert first["llm"]["status"] == second["llm"]["status"] == "available"
    assert first["llm"]["checked_at"] == second["llm"]["checked_at"]
