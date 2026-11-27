# Data Model: Walking Skeleton (Feature 001)

This feature creates no persistent business tables. The database gets only the Alembic baseline revision (`0001_baseline`) and its `alembic_version` bookkeeping table. The entities below are in-memory or wire models. Wire models are Pydantic models, published in the OpenAPI schema and turned into TypeScript types for the frontend.

## Settings (in-memory, loaded once at startup)

Source: environment variables, plus `../.env` when it is present (see [research.md R4](research.md#r4-configuration-loading-defaults-and-the-no-config-file-notice-fr-008-clarification-q2)). The full key list with defaults is in [contracts/configuration.md](contracts/configuration.md).

| Field | Type | Default | Validation |
|---|---|---|---|
| `llm_provider` | enum `fake` \| `ollama` \| `openai_compat` | `ollama` | Empty or unknown → startup error naming the allowed values |
| `ollama_base_url` | http(s) URL | `http://localhost:11434` | Valid URL |
| `ollama_model` | str | `llama3.2:3b` (may change per ADR-001) | Non-empty when provider is `ollama` |
| `openai_compat_base_url` | http(s) URL or empty | `""` | Required, valid URL when provider is `openai_compat` |
| `openai_compat_api_key` | SecretStr or empty | `""` | Required when provider is `openai_compat`; never printed |
| `openai_compat_model` | str | `""` | Required when provider is `openai_compat` |
| `llm_timeout_seconds` | float > 0 | `120` | Generation timeout |
| `embedding_model` | str | `BAAI/bge-small-en-v1.5` | Not used until Feature 003; kept so `.env.example` matches `Settings` |
| `data_dir` | path | `./data` | Must be creatable and writable (checked at startup) |
| `config_file_loaded` | bool | `false` | `true` only when it comes from `.env`; drives the startup notice |

Derived: `database_path = data_dir / "knowledge.sqlite3"`.

## LLM types (in-memory, `app/llm/types.py`)

- **ChatMessage**: `role` (`system` \| `user` \| `assistant`) and `content` (str).
- **Completion**: `text` (str), `model` (str) and `provider` (provider name).
- **Availability**: `status` (`available` \| `unavailable`), `reason` (str or null; required when unavailable; never contains secrets) and `checked_at` (UTC datetime).
- **LLMProviderError** (exception): `reason` (str, redacted). It is raised by `complete` and `stream` on failure.

## HealthReport (wire model, `GET /api/health`)

| Field | Type | Notes |
|---|---|---|
| `status` | `"ok"` | Always `"ok"` when the process is serving, because startup refuses to run with a broken store. The type is an enum so `"error"` can be added later without breaking compatibility |
| `version` | str | Application version from `pyproject.toml` |
| `database` | `DatabaseStatus` | |
| `llm` | `LLMStatus` | |

**DatabaseStatus**

| Field | Type | Notes |
|---|---|---|
| `status` | `"ok"` | Store opened and migrations applied |
| `schema_revision` | str | Alembic head revision, for example `0001_baseline` |
| `vector_search` | `"ok"` | Result of the sqlite-vec smoke check at startup |
| `vector_search_version` | str | Value of `vec_version()` |

**LLMStatus**

| Field | Type | Notes |
|---|---|---|
| `provider` | `"fake"` \| `"ollama"` \| `"openai_compat"` | |
| `model` | str | Configured model name. For `fake` it is `"fake"` |
| `status` | `"available"` \| `"unavailable"` | From the cached availability check (60-second TTL) |
| `reason` | str \| null | Readable reason when unavailable; null otherwise |
| `checked_at` | datetime (ISO 8601, UTC) | When the cached check ran |

Invariant: no field of `HealthReport` contains a URL query string, header value or API key. The base URL may appear inside `reason` (useful for troubleshooting reachability), but credentials never do.

## State transitions

**LLM availability** (per process, cached):

```text
            check() ok                      check() fails
 (none) ─────────────────▶ available ◀───────────────────▶ unavailable
              └──────────────────────────────▶ unavailable
 A transition happens only when the cache entry is ≥ 60 s old and a health request arrives.
```

**Startup**:

```text
load settings ──invalid──▶ exit(2) with one line per faulty setting
     │ ok
prepare data dir ──not writable──▶ exit(1) "data directory … is not writable"
     │
migrate to head ──error──▶ exit(1) with reason
     │
vector smoke check ──error──▶ exit(1) "vector search unavailable: …"
     │
serve (health = ok; LLM checked lazily on first health request)
```
