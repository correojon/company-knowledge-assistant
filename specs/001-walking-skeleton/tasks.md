---

description: "Task list for Feature 001: Walking Skeleton"
---

# Tasks: Walking Skeleton

**Input**: Design documents from `/specs/001-walking-skeleton/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required. Constitution IV (Test-First Quality Gate) and [docs/feature-workflow.md](../../docs/feature-workflow.md) say every behaviour task begins with a failing test. Each behaviour task below is written as **Test first → Implement**. Write the named tests, run them and confirm they fail, then implement until they pass. A task that only changes configuration or docs states how to verify it, and why it has no automated test.

**Done means**: the task's focused tests pass, plus `cd backend && uv run ruff check .` for backend tasks and `cd frontend && npm run lint && npm run build` for frontend tasks. Commit after each task, e.g. `feat(skeleton): add AvailabilityCache (spec 001, T007)`.

**Organization**: Tasks are grouped by user story. Constraint citations such as `data-model.md Settings.llm_provider` point to the canonical field definitions. Don't copy those constraints into code comments; implement them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: The user story the task belongs to (US1, US2, US3)

## Path Conventions

Web application: `backend/` (FastAPI package at `backend/app/`, tests at `backend/tests/{unit,integration,contract}/`) and `frontend/` (Vite app at `frontend/src/`, tests at `frontend/src/test/`). Repository-root files: `compose.yml`, `compose.ollama.yml`, `.env.example`, `README.md`, `.github/workflows/ci.yml`, `docs/adr/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Clean package layout and test tooling on both sides

- [X] T001 Clean up backend/pyproject.toml per research.md R14:
  - Delete `backend/src/backend/`.
  - Remove `[project.scripts]` and `[build-system]`, and replace the placeholder `description`.
  - Add `[tool.uv] package = false`.
  - Add `[tool.pytest.ini_options]` with `pythonpath = ["."]`, `testpaths = ["tests"]`, `asyncio_mode = "auto"` and `addopts = "--import-mode=importlib"`.
  - Add `[tool.ruff]` with `target-version = "py312"`, plus `[tool.ruff.lint] select = ["E","F","I","UP","B"]`.
  - Run `uv lock` to refresh backend/uv.lock.

  Verify: `uv sync && uv run ruff check .` passes. No tests exist yet, so pytest exit code 5 is expected until T004.
- [X] T002 [P] Create the empty backend package and test layout:
  - `backend/app/__init__.py` with `__version__ = "0.1.0"`, `backend/app/api/__init__.py` and `backend/app/llm/__init__.py`.
  - The directories `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/contract/` and `backend/scripts/`, each with a `.gitkeep` until it holds files.

  Leave the existing `backend/app/main.py` in place for now; T013 replaces it.
- [X] T003 [P] Add frontend test and type tooling in frontend/package.json and frontend/vite.config.ts:
  - `npm i -D vitest jsdom @testing-library/react @testing-library/jest-dom openapi-typescript`.
  - Add the script `"test": "vitest run"`.
  - Add a `test` block to vite.config.ts (`/// <reference types="vitest/config" />`) with `environment: "jsdom"`, `setupFiles: ["./src/test/setup.ts"]` and `passWithNoTests: true`.
  - Create frontend/src/test/setup.ts, which imports `@testing-library/jest-dom/vitest`.
  - If `tsc -b` cannot resolve the test types, add `"vitest/jsdom"` to `types` in tsconfig.app.json.

  Verify: `npm test`, `npm run lint` and `npm run build` all pass.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The network-free test harness, validated settings and the LLM provider abstraction that the health endpoint (US1) and provider switching (US2) both build on. `OllamaProvider.check()` is here because the default configuration (`LLM_PROVIDER=ollama`) must start in US1.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Network guard for all backend tests (US3-1, FR-014, research.md R11). **Test first**: in backend/tests/unit/test_network_guard.py, assert that `socket.create_connection(("127.0.0.1", 9))` and `socket.socket().connect(("127.0.0.1", 9))` both raise `NetworkBlockedError`, and that the message names the target address. **Implement** an autouse fixture in backend/tests/conftest.py that:
  - monkeypatches `socket.socket.connect` and `socket.create_connection` to raise `NetworkBlockedError` (defined in conftest.py);
  - deletes every key in contracts/configuration.md from `os.environ`;
  - sets `LLM_PROVIDER=fake` and `DATA_DIR=<tmp_path>/data`.
- [X] T005 Settings model in backend/app/config.py, covering data-model.md Settings.llm_provider, Settings.ollama_base_url, Settings.ollama_model, Settings.openai_compat_base_url, Settings.openai_compat_api_key, Settings.openai_compat_model, Settings.llm_timeout_seconds, Settings.embedding_model, Settings.data_dir and Settings.config_file_loaded, plus the derived `database_path` (research.md R4, R5).

  **Test first**, in backend/tests/unit/test_config.py:
  - Every default matches data-model.md, and `database_path == data_dir / "knowledge.sqlite3"`.
  - `llm_provider` rejects `""` and `"banana"`.
  - `ollama_base_url` and a non-empty `openai_compat_base_url` reject `"ftp://x"` and `"not a url"`.
  - `llm_timeout_seconds` rejects `0`.
  - A key set to `"sk-test-SECRET123"` does not appear in `repr(settings)` or `settings.model_dump_json()`.
  - `load_settings()` reads a `.env` file at `app.config.ENV_FILE` when it exists and ignores it when it is absent.

  **Implement**:
  - A pydantic-settings `Settings` class.
  - A module-level `ENV_FILE`, the repository-root `.env` resolved from `Path(__file__)`.
  - `load_settings()`, which calls `Settings(_env_file=ENV_FILE if ENV_FILE.exists() else None)` and reads `ENV_FILE` at call time.

  Leave the cross-field provider rules for T027. **Extend** backend/tests/conftest.py so the autouse fixture monkeypatches `app.config.ENV_FILE` to a non-existent path under `tmp_path`. Tests then never read the developer's `.env`.
- [X] T006 [P] LLM types, the `LLMProvider` Protocol and `FakeProvider` (US2-1, US3-2, FR-015, contracts/llm-provider.md).

  **Test first**, in backend/tests/unit/test_fake_provider.py:
  - The default reply is `"This is a canned reply from the fake provider."`.
  - Custom replies cycle in order, and `complete` and `stream` share one cycle.
  - The `stream` chunks join to exactly the reply, whitespace included.
  - `calls` records the messages each call received.
  - `check()` returns `available` with `reason is None`.
  - Two fresh instances given the same calls produce identical outputs.
  - `Availability(status="unavailable", reason=None)` raises a validation error.

  **Implement**:
  - backend/app/llm/types.py: `ChatMessage`, `Completion`, `Availability` and `LLMProviderError`, covering data-model.md ChatMessage.role, Completion.provider, Availability.status, Availability.reason, Availability.checked_at (UTC) and LLMProviderError.reason.
  - backend/app/llm/base.py: the `LLMProvider` Protocol.
  - backend/app/llm/fake.py: `FakeProvider`, which does no I/O.
- [X] T007 `AvailabilityCache` (FR-012, SC-008, research.md R7). **Test first**, in backend/tests/unit/test_availability_cache.py, with an injectable clock and a counting stub provider:
  - Two calls 59 s apart make one probe.
  - A call at exactly 60 s makes a second probe.
  - An `unavailable` result is also cached.
  - `asyncio.gather` of 5 concurrent calls makes 1 probe.

  **Implement** `AvailabilityCache(provider, ttl_seconds=60, clock=time.monotonic)` with an `asyncio.Lock` and an `async get() -> Availability` method, in backend/app/llm/base.py.
- [X] T008 `OllamaProvider.check()` (US2-4, FR-012, the "model not pulled" edge case, research.md R7). **Test first**, in backend/tests/integration/test_ollama_provider.py, using `httpx.MockTransport`:
  - The check sends only `GET /api/tags`. Assert that no POST is sent.
  - The model matches by exact name, or by name plus `:latest`.
  - A missing model gives `model 'X' not found; run: ollama pull X`.
  - Connection refused and timeout give `cannot reach <base_url> (is Ollama running?)`.
  - HTTP 503 gives `unexpected response (HTTP 503)`.
  - `check()` never raises.
  - The probe timeout is 3 s.

  **Implement** `OllamaProvider(base_url, model, timeout_seconds, transport=None)` in backend/app/llm/ollama.py, with `name = "ollama"` and `check()`. Have `complete` and `stream` raise `NotImplementedError` until T029.
- [X] T009 Provider factory. **Test first**, in backend/tests/unit/test_factory.py:
  - `fake` gives a `FakeProvider` with `model == "fake"`.
  - `ollama` gives an `OllamaProvider` carrying `ollama_base_url`, `ollama_model` and `llm_timeout_seconds` from Settings.

  **Implement** `build_provider(settings)` in backend/app/llm/factory.py. It raises nothing for reachability. The `openai_compat` mapping is added in T032.

**Checkpoint**: Foundation ready: `uv run pytest` is green with the network guard active.

---

## Phase 3: User Story 1 - One-command start with visible health (Priority: P1) 🎯 MVP

**Goal**: `docker compose up` from a fresh clone (with or without `.env`) starts the backend and frontend. The backend creates and migrates the SQLite store and passes the sqlite-vec self-check. The browser shows "Backend: healthy" inside a Documents/Search/Chat shell.

**Independent Test**: quickstart.md V1, V2, V3, V4 and V9. Clone into an empty folder, run `docker compose up --build` and open http://localhost:5173. It shows "Backend: healthy" and the three placeholder sections.

- [X] T010 [US1] Data directory and engine (FR-005, the "data dir not writable" edge case, research.md R8). **Test first**, in backend/tests/integration/test_startup.py:
  - `test_prepare_data_dir_creates_missing_dir`.
  - `test_unwritable_data_dir_fails`: on a `chmod 0o500` directory, it raises `StartupError` with the message `data directory '<path>' is not writable`. Skip it when running as root.
  - `test_engine_connection_has_vec_and_pragmas`: `SELECT vec_version()` returns a value, `PRAGMA journal_mode` is `wal` and `PRAGMA foreign_keys` is `1`.

  **Implement** in backend/app/db.py:
  - `StartupError`.
  - `prepare_data_dir(path)`, which creates the directory and writes then removes a probe file.
  - `create_db_engine(database_path)`, with a `connect` listener that enables extension loading, calls `sqlite_vec.load` and disables extension loading again, and sets both PRAGMAs.
- [ ] T011 [US1] Alembic baseline and migrate (US1-3, US1-4, FR-005). **Test first**, in backend/tests/integration/test_startup.py:
  - `test_migrate_fresh_store_to_head`: `alembic_version` holds `0001_baseline`.
  - `test_restart_reuses_store`: create a sentinel table with one row through `sqlite3`, call `migrate` again, and assert that the row still exists and the file's inode is unchanged.
  - `test_migration_failure_stops_startup`: with `alembic.command.upgrade` monkeypatched to raise, `migrate` raises `StartupError("migration failed: …")`.

  **Implement**:
  - backend/alembic.ini.
  - backend/migrations/script.py.mako.
  - backend/migrations/env.py, which takes the connection from `config.attributes["connection"]`, uses `render_as_batch=True`, and does not call `fileConfig` so app logging is left alone.
  - backend/migrations/versions/0001_baseline.py, which creates no tables.
  - In backend/app/db.py, `migrate(engine) -> str`, which runs `alembic.command.upgrade(cfg, "head")` programmatically, resolves `script_location` from the file's path, and returns the head revision. It wraps any exception in `StartupError("migration failed: <reason>")`.
- [ ] T012 [US1] Vector smoke check (US1-3, the "sqlite-vec fails to load" edge case). **Test first**, in backend/tests/integration/test_startup.py:
  - `test_vector_smoke_check_returns_version`: the check returns a non-empty version.
  - `test_vector_load_failure_stops_startup`: with `sqlite_vec.load` monkeypatched to raise, it raises `StartupError("vector search unavailable: …")`.

  **Implement** `vector_smoke_check(engine) -> str` in backend/app/db.py. It reads `SELECT vec_version()`. It then creates `temp.vec_smoke USING vec0(embedding float[4])`, inserts 3 vectors, asserts the expected nearest neighbour with a KNN `MATCH` query and drops the table. Any failure, extension loading included, becomes a `StartupError`.
- [ ] T013 [US1] Application factory and startup sequence (data-model.md "Startup" state transitions). **Test first**, in backend/tests/integration/test_startup.py:
  - `test_startup_creates_store_and_passes_smoke`: run `create_app(settings)` inside a `TestClient` context. The DB file exists, and `app.state` holds the schema revision and vec version.
  - `test_startup_failure_propagates`: with an unwritable `data_dir`, a `StartupError` is raised.

  **Implement** in backend/app/main.py:
  - `AppState`.
  - `startup(settings, provider=None) -> AppState`: prepare the data directory, migrate, run the smoke check, then build the provider with `build_provider` and wrap it in an `AvailabilityCache`.
  - `create_app(settings, *, state=None, provider=None)`, whose lifespan calls `startup` only when `state` is None.

  Delete the old `/health` route and the module-level `app`. Add an `app_factory` fixture to backend/tests/conftest.py that builds `Settings` with the fake provider and `data_dir` under `tmp_path`.
- [ ] T014 [US1] Health endpoint (US1-1, FR-003, US2-4 backend side, FR-012 caching, contracts/openapi-health.yaml). Models must cover data-model.md HealthReport.status, HealthReport.version, DatabaseStatus.status, DatabaseStatus.schema_revision, DatabaseStatus.vector_search, DatabaseStatus.vector_search_version, LLMStatus.provider, LLMStatus.model, LLMStatus.status, LLMStatus.reason and LLMStatus.checked_at.

  **Test first**, in backend/tests/integration/test_health.py:
  - `test_health_ok_with_fake_provider`: checks every field. `version == app.__version__`, and `llm` is `fake`/`fake`/`available` with `reason` null and `checked_at` in UTC.
  - `test_llm_unavailable_keeps_backend_ok`: pass an `OllamaProvider` with a `MockTransport` that raises `ConnectError` through `create_app(provider=...)`. `status` is `ok` and `llm.status` is `unavailable` with a reason.
  - `test_health_cached_within_60s`: two requests send 1 probe.

  Add backend/tests/unit/test_version.py, which asserts that `app.__version__` equals the version in backend/pyproject.toml (read with `tomllib`).

  **Implement** `HealthReport`, `DatabaseStatus` and `LLMStatus` in backend/app/api/health.py. Add an `APIRouter(prefix="/api")` with `GET /health` and `operation_id="getHealth"`, and include it in `create_app`.
- [ ] T015 [US1] Contract test (Constitution IX, FR-003). In backend/tests/contract/test_health_contract.py, load specs/001-walking-skeleton/contracts/openapi-health.yaml (repository path from `Path(__file__)`) and compare it with `create_app(...).openapi()`. Check that:
  - `/api/health` GET has `operationId == "getHealth"`.
  - For `HealthReport`, `DatabaseStatus` and `LLMStatus`, the property names, `required` lists and enum values match. Resolve `$ref`/`anyOf` for nullable `reason`.
  - Both contract examples pass `HealthReport.model_validate`.

  Use PyYAML, which `uvicorn[standard]` already installs. If `import yaml` fails, add `pyyaml` to the dev group only. Fix the models until the test passes.
- [ ] T016 [US1] Entry point and the missing-config notice (US1-6, FR-008, contracts/configuration.md "Startup errors" rows with exit code 1). **Test first**:
  - In backend/tests/unit/test_config.py, `test_notice_when_config_file_absent`: `startup_notice(settings)` returns exactly `Notice: no .env file found; using built-in defaults (copy .env.example to .env to customise).` when `config_file_loaded` is false, and `None` when it is true.
  - backend/tests/unit/test_main.py, with `uvicorn.run` monkeypatched:
    - `test_main_prints_notice_and_runs_uvicorn` checks the notice on stdout and that `uvicorn.run` is called with host `0.0.0.0` and port 8000.
    - `test_main_startup_error_exits_1` checks for `SystemExit(1)`, a stderr line starting `Startup failed: data directory`, and that `uvicorn.run` is not called.

  **Implement** `startup_notice` in backend/app/config.py. Implement `main()` in backend/app/__main__.py: `load_settings()` → print the notice → `state = startup(settings)`, which on `StartupError` prints `Startup failed: <reason>.` to stderr and exits 1 → `uvicorn.run(create_app(settings, state=state), host="0.0.0.0", port=8000)`.
- [ ] T017 [P] [US1] Rewrite .env.example to match the settings defaults (FR-008, US1-6, research.md R4). **Test first**, in backend/tests/unit/test_env_example.py:
  - Every key in the repo-root .env.example is either a `Settings` field or one of `BACKEND_PORT`, `FRONTEND_PORT` or `API_PROXY_TARGET`.
  - Every `Settings` field is present in the file.
  - Keys appear in the order of the contracts/configuration.md table.
  - `Settings(_env_file=<.env.example>)` equals `Settings(_env_file=None)` on every field except `config_file_loaded`, which is `True`.

  **Implement**: rewrite .env.example per contracts/configuration.md. `CONFIG_FILE_LOADED=true` comes first, and each key gets a one-line `#` comment above it.
- [ ] T018 [US1] OpenAPI export and generated frontend types (FR-016, research.md R10). **Test first**, in backend/tests/unit/test_export_openapi.py:
  - `export_openapi.main([str(tmp_path / "a.json")])` run twice gives byte-identical files that end in `\n`, use sorted keys and contain `components.schemas.HealthReport`.
  - Export still succeeds when `app.config.ENV_FILE` points to a file containing `LLM_PROVIDER=banana`, because the schema must not depend on local configuration. This test passes on its first run and becomes a regression guard once T027 rejects `banana`.

  **Implement** backend/scripts/export_openapi.py. It takes an optional output path (default `../frontend/src/api/openapi.json`), builds `create_app(Settings(_env_file=None, llm_provider="fake"))` without running the lifespan, and writes `json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"`.

  Add the script `"gen:api"` to frontend/package.json: `cd ../backend && uv run python scripts/export_openapi.py && cd ../frontend && openapi-typescript src/api/openapi.json -o src/api/schema.d.ts`. Add `src/api/schema.d.ts` to the ignores in frontend/eslint.config.js. Run `npm run gen:api` and commit frontend/src/api/openapi.json and frontend/src/api/schema.d.ts.
- [ ] T019 [US1] Typed API client (US1-2, research.md R9). **Test first**, in frontend/src/test/client.test.ts, with `fetch` stubbed by `vi.stubGlobal`. `getHealth()`:
  - resolves to the parsed body on 200;
  - rejects on a non-2xx status, on a fetch rejection and on invalid JSON;
  - aborts and rejects after 4000 ms when fetch never settles (use `vi.useFakeTimers`).

  **Implement** frontend/src/api/client.ts: `export type HealthReport = components["schemas"]["HealthReport"]` from `./schema`, and `getHealth(signal?)`, which fetches the relative URL `/api/health` with an `AbortController` timeout of 4000 ms.
- [ ] T020 [US1] `useHealth` hook and backend badge (US1-1, US1-2, FR-004). **Test first**, in frontend/src/test/HealthBadge.test.tsx, with fake timers and mocked `fetch`. The badge shows:
  - `Backend: checking…` before the first response, never a blank page;
  - `Backend: healthy` on an ok response;
  - `Backend: unreachable` within 10 s when fetch rejects, returns 500 or hangs;
  - `Backend: healthy` again on the next 5 s poll after recovery.

  Unmounting stops polling.

  **Implement** frontend/src/hooks/useHealth.ts, which polls `getHealth` every 5000 ms, never runs overlapping requests and cleans up on unmount. Implement frontend/src/components/HealthBadge.tsx, which shows the backend status only. The LLM badge is added in T035.
- [ ] T021 [US1] App shell with placeholders (US1-5, FR-006). **Test first**, in frontend/src/test/AppShell.test.tsx, with `fetch` mocked:
  - Navigation shows the entries Documents, Search and Chat.
  - Documents is selected by default.
  - Clicking each entry shows its heading and the text `not available yet`.
  - The health badge is rendered.

  **Implement**:
  - frontend/src/components/AppShell.tsx: a sidebar with state-based navigation and no router dependency.
  - frontend/src/components/Placeholder.tsx.
  - frontend/src/App.tsx: render `AppShell`.

  Delete the unused template files frontend/src/App.css, frontend/src/assets/hero.png, frontend/src/assets/react.svg and frontend/src/assets/vite.svg if nothing references them.
- [ ] T022 [P] [US1] API proxy in frontend/vite.config.ts (the cross-origin edge case, research.md R2). Set `server.proxy` and `preview.proxy` so `/api` goes to `process.env.API_PROXY_TARGET ?? "http://localhost:8000"`. No automated test: this is build configuration. Verify natively: `cd backend && uv run python -m app` plus `cd frontend && npm run dev`, then open http://localhost:5173. It shows "Backend: healthy" with no CORS error in the console.
- [ ] T023 [US1] Backend container: backend/Dockerfile and backend/.dockerignore (research.md R15).
  - Base image `python:3.12-slim`, with `COPY --from=ghcr.io/astral-sh/uv:<pinned> /uv /bin/uv`.
  - Cache the dependency layer by running `uv sync --frozen --no-dev --no-install-project` with only pyproject.toml and uv.lock copied.
  - Then copy `app/`, `migrations/` and `alembic.ini`.
  - Set `ENV DATA_DIR=/data`.
  - Add `HEALTHCHECK --interval=5s --timeout=4s --start-period=20s --retries=3` that uses `python -c` with `urllib.request` against `http://localhost:8000/api/health`. A short interval keeps the frontend's `depends_on: service_healthy` from delaying the UI by Docker's 30 s default (SC-002).
  - Set `CMD ["uv","run","--no-sync","python","-m","app"]`.
  - .dockerignore excludes `.venv`, `data`, `.env`, `tests`, `__pycache__`.

  Verify: `docker build -t cka-backend backend`, then `docker run -p 8000:8000 -e LLM_PROVIDER=fake cka-backend`. `curl localhost:8000/api/health` shows `vector_search: ok` (US1-3 in a container). Record the first build time. If it exceeds about 6 min, apply the R15 fallback.
- [ ] T024 [P] [US1] Frontend container: frontend/Dockerfile and frontend/.dockerignore (research.md R15). Use `node:26-slim`, copy package.json and package-lock.json, run `npm ci`, copy the source and run `npm run build`. Set `CMD ["npm","run","preview","--","--host","0.0.0.0","--port","5173"]`. .dockerignore excludes `node_modules`, `dist`, `.env`. Verify: `docker build frontend` succeeds.
- [ ] T025 [US1] compose.yml at the repository root (FR-001, FR-002, FR-007, research.md R1 and R3).
  - `backend` service:
    - `build: ./backend`, with `env_file: [{path: .env, required: false}]`.
    - `environment`: `DATA_DIR=/data` and `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
    - `extra_hosts: ["host.docker.internal:host-gateway"]`.
    - Port `"${BACKEND_PORT:-8000}:8000"` and volume `app-data:/data`.
  - `frontend` service:
    - `build: ./frontend`, with `environment: API_PROXY_TARGET=http://backend:8000`.
    - Port `"${FRONTEND_PORT:-5173}:5173"`, with `depends_on: backend: condition: service_healthy`.
  - A named volume `app-data`.

  No `ollama` service. Verify with quickstart V1, V2 (no `.env` → notice in `docker compose logs backend`), V3, V4 and V9.
- [ ] T026 [US1] Write the README getting-started sections (FR-018) in README.md:
  - prerequisites (Git, Docker with Compose ≥ 2.24; uv and Node 26 for native runs);
  - `cp .env.example .env` (optional: built-in defaults apply without it);
  - `docker compose up --build` and the address http://localhost:5173;
  - changing `FRONTEND_PORT`/`BACKEND_PORT` when a port is in use;
  - native run commands from contracts/configuration.md.

  Verify by following the README word for word in quickstart V1.

**Checkpoint**: User Story 1 is fully functional. Validate with quickstart V1–V4 and V9 before moving on.

---

## Phase 4: User Story 2 - Switch language model provider by configuration only (Priority: P2)

**Goal**: `LLM_PROVIDER` selects fake, ollama or openai_compat. Bad configuration stops startup with a clear message. An unreachable provider is a secondary "unavailable" status. Keys never leak. A dev check, an opt-in bundled Ollama and ADR-001 complete the story.

**Independent Test**: quickstart V5 (steps a–g plus the secret check) and V6.

- [ ] T027 [US2] Cross-field provider validation and readable errors (US2-5, FR-011, contracts/configuration.md "Startup errors" rows with exit code 2). This narrows data-model.md Settings.ollama_model, Settings.openai_compat_base_url, Settings.openai_compat_api_key and Settings.openai_compat_model to "required for the selected provider". It also covers Settings.llm_provider and Settings.ollama_base_url.

  **Test first**, in backend/tests/unit/test_config.py:
  - With `openai_compat`, each missing field among base URL, model and key raises a separate error.
  - `ollama` with an empty `ollama_model` fails.
  - `format_settings_errors(exc)` returns exactly the contract lines:
    - `Invalid configuration: LLM_PROVIDER='banana' is not allowed. Allowed values: fake, ollama, openai_compat.`
    - `Invalid configuration: OPENAI_COMPAT_API_KEY is required when LLM_PROVIDER=openai_compat.` (one line per missing field)
    - `Invalid configuration: OLLAMA_BASE_URL='ftp://x' is not a valid http(s) URL.`
  - The output never contains a key value.

  **Implement** a `model_validator(mode="after")` and `format_settings_errors(exc) -> list[str]`, which maps field names to upper-case env names, in backend/app/config.py.
- [ ] T028 [US2] Exit code 2 on bad configuration (US2-5, FR-011). **Test first**, in backend/tests/unit/test_main.py, `test_invalid_config_exits_2`: with `LLM_PROVIDER=banana`, `main()` raises `SystemExit(2)`, stderr contains the allowed-values line, and `uvicorn.run` and `startup` are not called. **Implement**: catch `ValidationError` from `load_settings()` in backend/app/__main__.py, print each `format_settings_errors` line to stderr and exit 2.
- [ ] T029 [US2] `OllamaProvider.complete` and `stream` (US2-2, FR-010, contracts/llm-provider.md wire formats and rule 1). **Test first**, in backend/tests/integration/test_ollama_provider.py, using `MockTransport`:
  - `POST /api/chat` sends `model`, `messages`, `stream: false` and `options.temperature`, plus `options.num_predict` only when `max_tokens` is set.
  - The text is parsed from `message.content` into a `Completion(provider="ollama")`.
  - `stream` sends `stream: true` and yields `message.content` per NDJSON line until `done: true`.
  - Connection errors, timeouts (`llm_timeout_seconds`), non-2xx responses and malformed JSON all raise `LLMProviderError` with a one-line reason.

  **Implement** in backend/app/llm/ollama.py, replacing the T008 stubs.
- [ ] T030 [P] [US2] `OpenAICompatProvider.check()` (US2-4, FR-012, hosted edge cases, research.md R7). **Test first**, in backend/tests/integration/test_openai_compat_provider.py:
  - The check sends only `GET {base}/models`, with `Authorization: Bearer <key>`.
  - The model matches by `id`, or by `id` with a `models/` prefix stripped.
  - Responses map to reasons: 401 and 403 give `provider rejected the API key (HTTP 401)`, 429 gives `provider rate limit reached (HTTP 429)`, 5xx gives `unexpected response (HTTP 5xx)`, and a connection error gives `cannot reach <base>`.
  - A trailing slash on the base URL is handled.
  - The key never appears in `Availability.reason` or in `caplog`.
  - The probe timeout is 3 s.

  **Implement** `OpenAICompatProvider(base_url, api_key: SecretStr, model, timeout_seconds, transport=None)` with `name = "openai_compat"` and `check()`, in backend/app/llm/openai_compat.py.
- [ ] T031 [US2] `OpenAICompatProvider.complete` and `stream` (US2-3, US2-6, FR-010, FR-013). **Test first**, in backend/tests/integration/test_openai_compat_provider.py:
  - `POST {base}/chat/completions` sends `model`, `messages`, `temperature` and `max_tokens`.
  - The text is parsed from `choices[0].message.content`.
  - `stream` parses SSE `data:` lines, yields `choices[0].delta.content`, skips empty deltas and stops at `data: [DONE]`.
  - Errors raise `LLMProviderError` with the same reason mapping as T030.
  - The key is absent from every `LLMProviderError.reason` and from `caplog`.

  **Implement** in backend/app/llm/openai_compat.py.
- [ ] T032 [US2] Factory mapping for `openai_compat`. **Test first**, in backend/tests/unit/test_factory.py: `openai_compat` settings give an `OpenAICompatProvider` with the configured base URL and model, and `repr(provider)` does not contain the key. **Implement** in backend/app/llm/factory.py.
- [ ] T033 [US2] End-to-end secret redaction check (US2-6, FR-013). **Test first**, in backend/tests/integration/test_secrets.py:
  - Use `openai_compat` settings with key `sk-test-SECRET123` and a provider whose `MockTransport` answers 401.
  - Run startup plus `GET /api/health` under `caplog` at DEBUG level.
  - Assert that the key, and its first 8 characters, are absent from the health JSON, every log record and `repr(settings)`.

  Prove the test can fail by temporarily logging the key. Fix any leak in backend/app/ before finishing.
- [ ] T034 [US2] Dev check command (FR-010, research.md R12). **Test first**, in backend/tests/unit/test_llm_check.py:
  - `main(["Say hello"])` with the fake provider prints `provider=fake model=fake`, then the streamed canned reply, and returns 0.
  - With no arguments, it uses a default prompt.
  - A provider that raises `LLMProviderError` makes it return 1, with the reason on stderr.

  **Implement** backend/app/llm/check.py, which uses `load_settings()` and `build_provider`, and streams to stdout with `flush=True`. Add an `if __name__ == "__main__": sys.exit(asyncio.run(...))` guard.
- [ ] T035 [US2] Secondary LLM badge (US2-4, FR-004). **Test first**, in frontend/src/test/HealthBadge.test.tsx:
  - An available model shows `LLM: ollama · llama3.2:3b — available`.
  - An unavailable model shows `LLM: ollama · llama3.2:3b — unavailable (cannot reach …)`, and the badge still reads `Backend: healthy`.
  - The LLM badge is hidden while the backend is unreachable.

  **Implement** in frontend/src/components/HealthBadge.tsx.
- [ ] T036 [US2] Opt-in bundled Ollama: compose.ollama.yml at the repository root (FR-007, research.md R3).
  - `ollama` service: image `ollama/ollama`, volume `ollama-models:/root/.ollama`, and a healthcheck that runs `ollama list`.
  - `ollama-pull` one-shot service: same image, `environment: OLLAMA_HOST=http://ollama:11434`, `entrypoint: ["ollama","pull","${OLLAMA_MODEL:-llama3.2:3b}"]`, `depends_on: ollama: condition: service_healthy`, `restart: "no"`.
  - `backend` override: `environment: OLLAMA_BASE_URL=http://ollama:11434` and `depends_on: ollama`.

  No automated test: this is infrastructure. Verify with quickstart V6, including that plain `docker compose up` still starts only `backend` and `frontend`.
- [ ] T037 [US2] Citation spike script (FR-019, research.md R13). **Test first**, in backend/tests/unit/test_citation_spike.py:
  - `is_compliant(reply, n_sources=3)` returns true for `"... [1]"` and `"[1][3]"`, and false for no marker, `"[0]"` and `"[4]"`.
  - `run_spike(provider_for_model, models)` with a `FakeProvider` returns a 5-prompt × N-model result table.
  - `PROMPTS` has exactly 5 entries, each with 3 numbered sources.

  **Implement** backend/scripts/citation_spike.py: `PROMPTS`, `is_compliant` and `run_spike`. Its `main(argv)` builds an `OllamaProvider` per model given on the command line, from `load_settings()`, and prints a Markdown table of compliance per prompt and per model.
- [ ] T038 [US2] Run the spike and write ADR-001 (FR-019). This needs a host Ollama, so a person runs it:
  - Run `cd backend && uv run python scripts/citation_spike.py llama3.2:3b <candidate2> [<candidate3>]` with instruction-tuned models of 4B parameters or fewer.
  - Write docs/adr/001-local-model.md with Context, Decision, Consequences, Alternatives and the pasted results table.
  - If the winner is not `llama3.2:3b`, update the `ollama_model` default in backend/app/config.py, plus .env.example, the compose.ollama.yml fallback, contracts/configuration.md, data-model.md and the openapi-health.yaml examples. T005 and T017 catch any mismatch.
- [ ] T039 [US2] Write the README provider sections (FR-018) in README.md:
  - switching `LLM_PROVIDER` between `fake`, `ollama` and `openai_compat`, with a free-tier example (`OPENAI_COMPAT_BASE_URL=https://api.groq.com/openai/v1`) and the restart command;
  - the dev check command, both native and in a container;
  - the opt-in bundled Ollama command;
  - troubleshooting:
    - host Ollama on Linux or WSL2 without Docker Desktop needs `OLLAMA_HOST=0.0.0.0:11434`, set through a systemd override;
    - a model that is not pulled: run `ollama pull`;
    - 401 and 429 responses from the hosted provider;
  - a note that `.env` is git-ignored and keys are never logged;
  - a link to docs/adr/001-local-model.md.

**Checkpoint**: User Stories 1 and 2 both work. Validate with quickstart V5 and V6.

---

## Phase 5: User Story 3 - Trustworthy automated checks without a real model (Priority: P3)

**Goal**: The full suite passes with no model and no network, repeatably and in under 2 minutes. CI runs backend lint and tests plus frontend lint, tests and build, and fails on stale contract types or a container that doesn't start healthy.

**Independent Test**: quickstart V7 (Ollama stopped, `LLM_PROVIDER=ollama` in `.env`, 10 consecutive green runs in under 2 min), V8 (contract drift fails CI, regenerating fixes it), and the CI `container` job is green.

- [ ] T040 [US3] Isolation from the developer's environment (US3-1, US3-2, FR-014). **Test first**, in backend/tests/unit/test_isolation.py:
  - `test_settings_ignore_developer_env_file`: with a repo-root-style `.env` written to a temporary path containing `LLM_PROVIDER=ollama`, `load_settings()` inside tests still yields `fake`, because `app.config.ENV_FILE` points under `tmp_path`.
  - `test_shell_llm_vars_are_cleared`: set `OPENAI_COMPAT_API_KEY` in `os.environ` before the fixture runs, using `pytest`'s `pytester` or a subprocess run of pytest with that env. It is absent inside the test.

  **Implement** any missing isolation in backend/tests/conftest.py.
- [ ] T041 [US3] CI test and lint coverage (FR-017) in .github/workflows/ci.yml:
  - `backend` job: `uv sync --frozen`, `uv run ruff check .` and `uv run pytest`.
  - `frontend` job: `node-version: 26`, `npm ci`, `npm run lint`, `npm test` and `npm run build`.

  No automated test: this is CI configuration. Verify by pushing the branch and seeing both jobs green.
- [ ] T042 [US3] Contract drift job (US3-3, US3-4, FR-017, SC-006, research.md R10). Add a `contract` job to .github/workflows/ci.yml:
  - Set up uv and Node 26, then run `cd backend && uv sync --frozen`, `cd frontend && npm ci` and `npm run gen:api`.
  - Run `git diff --exit-code -- frontend/src/api`. On failure, print `API contract types are stale. Run: cd frontend && npm run gen:api, then commit the result.` and `exit 1`.

  Verify with quickstart V8 on a scratch branch: the job fails, then passes after regenerating.
- [ ] T043 [US3] Container smoke job (US1-3 inside a container, the cross-origin edge case, FR-017, Constitution IV integration-boundary coverage). Add a `container` job to .github/workflows/ci.yml:
  - `docker compose up -d --build --wait --wait-timeout 300`. No `.env` is present, so this also exercises the built-in defaults from US1-6.
  - `curl -fsS localhost:8000/api/health`, then assert `status == "ok"`, `database.vector_search == "ok"` and a non-empty `vector_search_version`. Use `python3 -c` with `json`.
  - `curl -fsS localhost:5173/api/health` succeeds, which proves the frontend proxy reaches the backend.
  - `docker compose logs backend | grep "no .env file found"` finds the notice.
  - On failure, `docker compose logs`. Always, `docker compose down -v`.

  The default `LLM_PROVIDER=ollama` shows `llm.status: unavailable` in CI. That is expected: don't assert on it. Verify by pushing and seeing the job green.
- [ ] T044 [US3] Write the README testing section (FR-018) in README.md: backend and frontend test, lint and build commands from contracts/configuration.md; that tests never need a model and always use the fake provider; the network guard; `npm run gen:api` and the CI contract check.

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and cleanup across stories

- [ ] T045 [P] Replace the template boilerplate in backend/README.md and frontend/README.md with a short pointer to the root README.md and the commands that apply to each folder.
- [ ] T046 [P] Secret and ignore check (SC-007, quickstart V10): `git log -p | grep -iE "api[_-]?key\s*=\s*\S{8,}"` prints nothing, and `git check-ignore .env data/` succeeds. Fix .gitignore if needed.
- [ ] T047 Run quickstart V7 locally with Ollama stopped and `LLM_PROVIDER=ollama` in `.env`. Expect 10 consecutive `uv run pytest -q -p no:cacheprovider` runs, all green, under 2 min each (SC-004, SC-005), and the frontend checks green. Fix any flaky test in backend/tests/ or frontend/src/test/ at its root cause. Never weaken an assertion.
- [ ] T048 Full quickstart validation in a fresh clone in a temporary folder: V1–V6, V8–V10, following README.md word for word. Record the first build time and the time to healthy (SC-001, SC-002, SC-003, SC-008). Correct README.md or the affected file for every deviation, and update specs/001-walking-skeleton/spec.md first if reality differs from the spec.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T002 and T003 can run alongside T001.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories.
- **US1 (Phase 3)**: Depends on Foundational.
- **US2 (Phase 4)**: Depends on Foundational. T035 extends T020's `HealthBadge`, T028 extends T016's `__main__` and T036 extends T025's `compose.yml`. In practice, do US2 after US1.
- **US3 (Phase 5)**: Depends on Foundational. T042 needs T018 (`gen:api`), and T041 needs T003 (`npm test`).
- **Polish (Phase 6)**: Depends on all stories.

### User Story Dependencies

- **US1 (P1)**: Needs only Foundational. With the default `LLM_PROVIDER=ollama`, the LLM section shows `unavailable` until a host Ollama runs. That is expected, and the backend stays healthy.
- **US2 (P2)**: Backend work (T027–T034, T037) needs only Foundational. UI and compose work (T035, T036) builds on US1 files.
- **US3 (P3)**: Needs Foundational, plus T018 from US1 for the contract job.

### Within Each Story

- Write the failing test, run it and see it fail, then implement.
- db.py tasks run in order: T010 → T011 → T012 → T013 → T014 → T015 → T016.
- T018 (generated types) comes before T019 → T020 → T021.
- Containers (T023, T024) come before compose (T025) and the README (T026).

### Parallel Opportunities

- Setup: T002 ∥ T003.
- Foundational: T006 ∥ T005, which touch different files once T004 is done. T007 and T008 both need T006.
- US1: T017 (.env.example), T022 (vite proxy) and T024 (frontend Dockerfile) can each run beside the backend chain.
- US2: T030 (openai_compat.py) ∥ T029 (ollama.py). T037 (spike script) is independent of T027–T036.
- US3: T040 is independent of T041, T042 and T043, which share ci.yml and so run in sequence.
- Polish: T045 ∥ T046.

---

## Parallel Example: User Story 1

```bash
# After T016, while the backend chain continues:
Task: "T017 Rewrite .env.example and add parity test in backend/tests/unit/test_env_example.py"
Task: "T022 API proxy in frontend/vite.config.ts"
Task: "T024 Frontend container: frontend/Dockerfile and frontend/.dockerignore"
```

## Parallel Example: User Story 2

```bash
Task: "T029 OllamaProvider.complete/stream in backend/app/llm/ollama.py"
Task: "T030 OpenAICompatProvider.check in backend/app/llm/openai_compat.py"
Task: "T037 Citation spike script in backend/scripts/citation_spike.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup (T001–T003).
2. Phase 2: Foundational (T004–T009). This phase is critical.
3. Phase 3: US1 (T010–T026).
4. **Stop and validate**: run quickstart V1–V4 and V9. A fresh clone shows "Backend: healthy".

### Incremental Delivery

1. Setup plus Foundational make the test harness and provider core green.
2. US1 gives a runnable app with a health badge: the MVP demo.
3. US2 adds provider switching, the dev check, bundled Ollama and ADR-001.
4. US3 adds CI hardening and the contract drift gate.
5. Polish runs the full quickstart in a fresh clone.

### Working Agreement

- Implement one task per `/speckit-implement` run, and commit after each.
- If reality differs from the spec, update the spec first, then the code.

---

## Notes

- [P] tasks touch different files and don't depend on incomplete tasks.
- [Story] labels map each task to a user story for traceability, and acceptance-scenario IDs (US1-1 …) map it to spec.md.
- Never edit or delete a test only to make it pass (Constitution IV).
- Never commit `.env`, keys or `data/`.
