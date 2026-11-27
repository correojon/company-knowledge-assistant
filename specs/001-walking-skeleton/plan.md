# Implementation Plan: Walking Skeleton

**Branch**: `001-walking-skeleton` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-walking-skeleton/spec.md`

## Summary

Deliver a runnable skeleton:
- `docker compose up` starts a FastAPI backend and a React web interface.
- The backend validates its configuration before starting, migrates a SQLite store and proves sqlite-vec works.
- The backend exposes `GET /api/health`, which reports data store and language model status. The model status comes from a quota-free check cached for 60 seconds.
- The web interface shows the health badge inside a Documents/Search/Chat shell.
- A hand-written `LLMProvider` interface has fake, Ollama and OpenAI-compatible implementations, all chosen by `LLM_PROVIDER`.
- Tests never touch the network: a socket guard and `FakeProvider` ensure it.
- CI fails when the frontend's generated OpenAPI types are stale.
- An ADR records the default local model, based on a citation-format spike.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript ~6.0 with React 19 on Node 26 (frontend)

**Primary Dependencies**:
- Backend, already declared: FastAPI, pydantic-settings, SQLModel, Alembic, sqlite-vec, httpx, uvicorn.
- Frontend, already installed: React, Vite 8, Tailwind 4, shadcn/ui.
- New frontend dev dependencies: `openapi-typescript`, `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`. No new backend dependencies.

**Storage**: SQLite file `DATA_DIR/knowledge.sqlite3` with the sqlite-vec extension loaded on every connection; Alembic migrations run at startup; named Docker volume `app-data`

**Testing**: pytest with FastAPI `TestClient`, `httpx.MockTransport` and an autouse socket guard; ruff; Vitest with Testing Library (jsdom); `tsc -b` and `vite build`; CI contract-drift job

**Target Platform**: Docker Compose on Linux, macOS, and Windows through WSL2; native dev runs with uv and npm

**Project Type**: Web application (backend and frontend)

**Performance Goals**: Started and healthy within 60 s of `docker compose up` once built (SC-002); health endpoint answers in under 3.5 s in the worst case (3 s probe timeout) and under 100 ms when cached; backend test suite under 2 min (SC-004)

**Constraints**: Zero cost; no secrets in logs or health output; at most 60 provider probes per hour (SC-008); "unreachable" shown within 10 s (5 s poll, 4 s timeout); the default command never downloads a model

**Scale/Scope**: Single user on a local machine; 1 endpoint, 3 providers, 1 UI page (shell plus badge), 1 ADR

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Status |
|---|---|---|
| I. Zero cost | Default provider is local Ollama; the hosted option targets free tiers through a generic OpenAI-compatible client; health probes use no quota (R7) | PASS |
| II. Grounded answers | No answers yet. The ADR-001 spike chooses the default model by citation-format compliance (R13), laying the groundwork | PASS (n/a for runtime) |
| III. Simple by default | One SQLite file; no queues or auth; the Ollama container is opt-in only (R3) | PASS |
| IV. Test-first | Every acceptance scenario maps to a test written first (see Verification map); socket guard and `FakeProvider` (R11) | PASS |
| V. No framework magic | Providers written by hand on httpx; no LangChain, LiteLLM or vendor SDKs (R6) | PASS |
| VI. Reproducible | `docker compose up` runs everything; configuration only through environment variables; `.env` git-ignored; defaults identical to `.env.example`, enforced by a test (R4) | PASS |
| VII. Documented decisions | `docs/adr/001-local-model.md` (required); this research.md records the other choices | PASS |
| VIII. Scope fixed | No auth, integrations or paid APIs | PASS |
| IX. Clear and stable contracts | Pydantic `HealthReport`; OpenAPI-generated TypeScript types; CI drift check (R10) | PASS |
| X. Security and data stewardship | `SecretStr` for the key; redacted reasons; secret check in quickstart V5 and V10 | PASS |
| XI. Maintainable simplicity | Only frontend test and type tooling added; no runtime client library; removal of the duplicate `src/backend` package (R14) | PASS |
| Tech constraints | Python 3.12+, FastAPI, pydantic-settings, SQLModel, SQLite with vector extension, uv, React/TS/Vite/Tailwind, ruff, pytest, existing CI extended | PASS |

**Post-design re-check (after Phase 1)**: PASS. The design adds no services beyond backend and frontend in the default command, and no new runtime dependencies. One new CI job (`contract`) adds to the merge gate without replacing it.

## Project Structure

### Documentation (this feature)

```text
specs/001-walking-skeleton/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R15
├── data-model.md        # Phase 1: Settings, LLM types, HealthReport, state transitions
├── quickstart.md        # Phase 1: validation runbook V1–V10
├── contracts/
│   ├── openapi-health.yaml   # GET /api/health
│   ├── llm-provider.md       # internal LLMProvider interface
│   └── configuration.md      # environment variables, startup errors, commands
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
compose.yml                    # backend + frontend (default command)
compose.ollama.yml             # opt-in: ollama + ollama-pull, overrides backend OLLAMA_BASE_URL
.env.example                   # every setting, with CONFIG_FILE_LOADED sentinel
README.md                      # prerequisites, start, switching providers, tests, troubleshooting
docs/adr/001-local-model.md
.github/workflows/ci.yml       # backend, frontend, contract jobs

backend/
├── Dockerfile
├── .dockerignore
├── pyproject.toml             # package=false, pytest/ruff config; src/backend removed
├── alembic.ini
├── migrations/
│   ├── env.py                 # render_as_batch, uses app.db engine
│   └── versions/0001_baseline.py
├── app/
│   ├── __main__.py            # load settings (friendly errors, exit 2) → notice → uvicorn.run
│   ├── main.py                # create_app(settings), lifespan startup sequence
│   ├── config.py              # Settings, format_settings_errors()
│   ├── db.py                  # engine with sqlite-vec loader, prepare_data_dir, migrate, vector_smoke_check
│   ├── api/
│   │   └── health.py          # GET /api/health, HealthReport models
│   └── llm/
│       ├── types.py           # ChatMessage, Completion, Availability, LLMProviderError
│       ├── base.py            # LLMProvider Protocol, AvailabilityCache
│       ├── fake.py
│       ├── ollama.py
│       ├── openai_compat.py
│       ├── factory.py         # build_provider(settings)
│       └── check.py           # python -m app.llm.check
├── scripts/
│   ├── export_openapi.py
│   └── citation_spike.py
└── tests/
    ├── conftest.py            # socket guard, fake provider, tmp DATA_DIR, app factory fixture
    ├── unit/                  # config, env-example parity, fake provider, availability cache, error formatting
    ├── integration/           # startup (migrate + smoke), health endpoint, ollama/openai_compat via MockTransport
    └── contract/              # HealthReport schema matches contracts/openapi-health.yaml

frontend/
├── Dockerfile
├── .dockerignore
├── vite.config.ts             # server/preview proxy /api → API_PROXY_TARGET; vitest config
├── package.json               # scripts: test, gen:api
└── src/
    ├── api/
    │   ├── openapi.json       # generated, committed
    │   ├── schema.d.ts        # generated, committed
    │   └── client.ts          # getHealth() typed fetch wrapper with timeout
    ├── hooks/useHealth.ts     # 5 s poll, 4 s timeout
    ├── components/
    │   ├── AppShell.tsx       # sidebar: Documents, Search, Chat
    │   ├── HealthBadge.tsx    # Backend: healthy/unreachable + LLM secondary badge
    │   └── Placeholder.tsx
    ├── App.tsx
    └── test/                  # HealthBadge, AppShell tests; setup file
```

**Structure Decision**: Web application layout using the existing `backend/` and `frontend/` folders. The backend package stays at `backend/app/` (where `main.py` already lives), and the unused `uv init` package `backend/src/backend/` is removed (R14). Tests are split into unit, integration and contract folders to match the constitution's emphasis on integration boundaries.

## Verification map (acceptance scenario → test or check)

| Spec item | Verified by |
|---|---|
| US1-1, SC-002 | quickstart V1; `tests/integration/test_health.py::test_health_ok_with_fake_provider`; `HealthBadge` "healthy" test |
| US1-2 | `HealthBadge` tests: fetch rejects, timeout after 4 s and non-2xx → "unreachable"; recovery on the next poll (fake timers); quickstart V4 |
| US1-3, FR-005 | `tests/integration/test_startup.py`: fresh `tmp_path` → DB file created, revision at head, `vec_version()` and KNN smoke pass; CI (native) plus quickstart V1 (container) |
| US1-4 | `test_startup.py::test_restart_reuses_store`: sentinel row in `alembic_version`, second startup, file not recreated |
| US1-5, FR-006 | `AppShell` test: three nav entries, each shows its placeholder |
| US1-6, FR-008 | `tests/unit/test_config.py::test_notice_when_config_file_absent`; `test_env_example_parity`; quickstart V2 |
| US2-1, FR-015 | `tests/unit/test_fake_provider.py` (canned, cycling, stream join, calls recorded) with the socket guard active |
| US2-2, US2-3, FR-010 | `tests/integration/test_ollama_provider.py` and `test_openai_compat_provider.py` (MockTransport: request shape, complete, stream); quickstart V5 dev check |
| US2-4, FR-012 | `test_health.py::test_llm_unavailable_keeps_backend_ok`; provider `check()` reason-mapping tests; `HealthBadge` secondary-status test |
| US2-5, FR-011 | `test_config.py`: empty or unknown provider; missing `openai_compat` fields; invalid URL; `format_settings_errors` output; `__main__` exits with code 2 |
| US2-6, FR-013 | Tests assert the key is absent from `repr(settings)`, health JSON, `LLMProviderError.reason` and captured logs (`caplog`) |
| FR-012 cache, SC-008 | `tests/unit/test_availability_cache.py`: injectable clock; 2 health calls within 60 s → 1 probe; at 60 s → second probe; concurrent calls → 1 probe |
| US3-1, US3-2, FR-014 | Autouse socket guard in `conftest.py`, plus a test asserting the guard raises on a real connect attempt |
| US3-3, US3-4, FR-016, FR-017, SC-006 | CI `contract` job; quickstart V8 |
| FR-018 | README review in quickstart V1 (steps followed verbatim) |
| FR-019 | `docs/adr/001-local-model.md` exists with a 5-prompt × ≥2-model compliance table |
| Edge: data dir not writable | `test_startup.py::test_unwritable_data_dir_fails` (read-only `tmp_path`) |
| Edge: sqlite-vec fails to load | `test_startup.py::test_vector_load_failure_stops_startup` (monkeypatched loader) |
| Edge: model not pulled, 401, 429 | Provider `check()` tests with MockTransport responses |
| SC-005 | quickstart V7 (10 consecutive runs) |

## Implementation order (input for /speckit-tasks)

1. **Backend hygiene**: pyproject cleanup (R14), ruff and pytest config, `conftest.py` with the socket guard and its test.
2. **Configuration**: `Settings`, error formatting, `.env.example` rewrite, parity test.
3. **LLM layer**: types, `FakeProvider`, `AvailabilityCache`, `OllamaProvider`, `OpenAICompatProvider`, factory, `app.llm.check`.
4. **Data store**: engine with sqlite-vec, data dir check, Alembic baseline, smoke check, startup sequence.
5. **Health API**: `HealthReport`, `/api/health`, `__main__` entry point, contract test against `openapi-health.yaml`.
6. **Frontend tooling**: Vitest and Testing Library, proxy config, `export_openapi.py` and `gen:api`, committed generated types.
7. **Frontend UI**: `client.ts`, `useHealth`, `HealthBadge`, `AppShell` and placeholders.
8. **Containers**: Dockerfiles, `compose.yml`, `compose.ollama.yml`, `.dockerignore`.
9. **CI**: frontend lint and test steps, `contract` job.
10. **Docs**: README and ADR-001 (run the spike, set the default model).
11. **Validation**: quickstart V1–V10.

## Complexity Tracking

No constitution violations to justify.
