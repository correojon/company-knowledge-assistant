# Research: Walking Skeleton (Feature 001)

Each entry: **Decision**, **Rationale**, **Alternatives considered**. Spec references are to [spec.md](spec.md).

## R1. Single start command and service layout

**Decision**: `docker compose up` from the repository root, with a `compose.yml` holding two services: `backend` (FastAPI on port 8000) and `frontend` (built Vite app served by `vite preview` on port 5173). Host ports come from compose variables `BACKEND_PORT` (default 8000) and `FRONTEND_PORT` (default 5173).

**Rationale**: Constitution VI names `docker compose up` as the start path. Two services mirror the two codebases and keep the frontend container stateless. `vite preview` serves the production build, which is fast to start (SC-002) and identical to what CI builds, while still supporting the same proxy configuration as the dev server.

**Alternatives considered**:
- Backend serves the built frontend as static files (one container): fewer moving parts, but couples the two builds and moves the UI off the port the roadmap and spec name (5173).
- Vite dev server in the container: hot reload is not needed by evaluators, and developers who want it run `npm run dev` natively.
- nginx for the frontend: one more technology to learn and configure for no benefit at this stage.

## R2. Frontend-to-backend connectivity (CORS edge case)

**Decision**: The frontend calls relative URLs under `/api`. Vite's `server.proxy` and `preview.proxy` forward `/api` to `API_PROXY_TARGET` (default `http://localhost:8000`; compose sets `http://backend:8000`). All backend routes live under the `/api` prefix.

**Rationale**: The browser only ever talks to its own origin, so cross-origin restrictions never apply with the defaults (spec edge case). No CORS middleware or origin settings are needed (Constitution XI). The `/api` prefix leaves room for the frontend's own routes later.

**Alternatives considered**: CORS middleware with an allowed-origins setting: works, but adds a setting and a class of misconfiguration that the proxy avoids entirely.

## R3. Optional local model service (FR-007, clarification Q1)

**Decision**: The default `compose.yml` does not run Ollama. It points the backend at the host with `OLLAMA_BASE_URL=http://host.docker.internal:11434` and `extra_hosts: ["host.docker.internal:host-gateway"]`. An override file `compose.ollama.yml` adds an `ollama` service (official `ollama/ollama` image, named volume for models), a one-shot `ollama-pull` service that runs `ollama pull $OLLAMA_MODEL`, and overrides the backend's `OLLAMA_BASE_URL` to `http://ollama:11434`. Opt-in command: `docker compose -f compose.yml -f compose.ollama.yml up`.

**Rationale**: The default command never downloads a model (clarification Q1). The override file switches the URL automatically, so users don't have to edit `.env` to opt in. `host-gateway` makes `host.docker.internal` work on Linux; Docker Desktop (macOS, Windows/WSL2) provides it natively.

**Known pitfall (README troubleshooting)**: on Linux and inside WSL2 without Docker Desktop, a host Ollama listens on `127.0.0.1` only, so containers cannot reach it through the host gateway. The fix is to run it with `OLLAMA_HOST=0.0.0.0:11434` (systemd override `Environment=OLLAMA_HOST=0.0.0.0:11434`), or to use the opt-in compose variant.

**Alternatives considered**:
- Compose `profiles: [ollama]`: profiles can add the service but cannot change the backend's URL, so users would have to edit two things.
- `network_mode: host`: not supported the same way on Docker Desktop, and it breaks service-name networking.

## R4. Configuration loading, defaults and the "no config file" notice (FR-008, clarification Q2)

**Decision**:
- One `Settings` class (pydantic-settings) holds every backend setting with its default. It is the single source of truth for defaults.
- Local runs read `../.env` (the repository root) when the file exists. Compose passes it with `env_file: [{path: .env, required: false}]`, so a missing file is not an error.
- `.env.example` starts with `CONFIG_FILE_LOADED=true`. The backend prints `Notice: no .env file found; using built-in defaults (copy .env.example to .env to customise).` when that variable is absent. The same check works locally and in containers, where the file itself is not visible.
- A unit test checks that every key in `.env.example` is either a `Settings` field with the same default value or one of the listed compose-only keys (`BACKEND_PORT`, `FRONTEND_PORT`, `API_PROXY_TARGET`). This guarantees "built-in defaults identical to the example file".

**Rationale**: Inside a container the backend cannot tell whether a host `.env` existed. A sentinel variable carried by the file is the simplest reliable signal, and it needs no bind mount (a missing bind-mount source would be created as a directory by Docker). The parity test turns an easily forgotten rule into a failing test.

**Alternatives considered**:
- Bind-mount `.env` into the container: fails or misbehaves when the file is missing.
- A wrapper script that copies `.env.example` automatically: rejected in clarification Q2 (option C).
- Repeating defaults in `compose.yml` as `${VAR:-default}`: duplicates the defaults in a third place.

## R5. Provider selection values and validation (FR-009, FR-011, FR-013)

**Decision**: `LLM_PROVIDER` accepts `fake`, `ollama` or `openai_compat`. These are the spec's "fake", "local" and "hosted"; the existing `.env.example` and the roadmap already use these values. The default is `ollama`. Validation runs before the server starts:
- An empty or unknown value fails.
- `openai_compat` requires `OPENAI_COMPAT_BASE_URL`, `OPENAI_COMPAT_MODEL` and `OPENAI_COMPAT_API_KEY` to be non-empty.
- `OLLAMA_BASE_URL` and `OPENAI_COMPAT_BASE_URL` must be valid http(s) URLs.

The backend's entry point (`python -m app`) loads settings. On `ValidationError` it prints one line per faulty setting, for example `Invalid configuration: LLM_PROVIDER='foo' is not allowed. Allowed values: fake, ollama, openai_compat.`, and exits with code 2 before uvicorn starts. API keys are `SecretStr`, so they never appear in reprs, logs, errors or health output.

**Rationale**: Validating before startup means there is no silent fallback (FR-011), and uvicorn's lifespan traceback is replaced by a readable message. `SecretStr` makes redaction the default instead of something each log call has to remember.

**Alternatives considered**: Validating inside the FastAPI lifespan: the app dies with a long traceback that buries the message.

## R6. Provider interface and implementations (FR-009, FR-010, FR-015)

**Decision**: A `typing.Protocol` named `LLMProvider` with three async methods: `complete(messages, *, max_tokens, temperature) -> Completion`, `stream(messages, ...) -> AsyncIterator[str]` and `check() -> Availability`. Three implementations are written by hand on `httpx.AsyncClient`, with no vendor SDKs:
- `FakeProvider`: constructed with an optional list of canned replies (default `"This is a canned reply from the fake provider."`). It cycles through them deterministically, streams a reply as whitespace-preserving word chunks, records the calls it receives for assertions, and makes no I/O. `check()` always reports available.
- `OllamaProvider`: native `POST /api/chat` (`stream: false` for `complete`; NDJSON lines for `stream`). The native API is chosen over Ollama's OpenAI-compatible endpoint because Feature 006 needs per-request `options.num_ctx` to control the context window.
- `OpenAICompatProvider`: `POST {base}/chat/completions` with `Authorization: Bearer`. `stream` parses `data:` SSE lines until `[DONE]`. This works with free tiers that expose an OpenAI-compatible API (for example Groq, or Google AI Studio's OpenAI-compatible endpoint).

A factory `build_provider(settings)` maps `LLM_PROVIDER` to an implementation. Errors are raised as `LLMProviderError(reason)`, where `reason` is a short message that never contains the key.

**Rationale**: Constitution I and V require a provider abstraction written by hand, with no framework magic. A Protocol keeps the fakes trivial. `httpx` is already a dependency, and its `MockTransport` lets provider tests run without a network.

**Alternatives considered**: LangChain or LiteLLM (violates Constitution V and adds large dependencies); the `openai` SDK (an extra dependency for two endpoints).

## R7. Availability check and cache (FR-012, clarification Q3, SC-008)

**Decision**: `check()` generates nothing:
- Ollama: `GET /api/tags`. The configured model counts as present if a returned `name` equals it, or equals it with `:latest` appended.
- OpenAI-compatible: `GET {base}/models`. The model is present if a returned `id` equals it, or equals it once a `models/` prefix is stripped (Google's OpenAI-compatible endpoint returns that prefix).

Each probe has a 3-second timeout. An `AvailabilityCache` wraps the provider: it returns the cached result while it is less than 60 seconds old, and an `asyncio.Lock` ensures only one probe runs at a time. It is fed by an injectable clock so tests are deterministic.

Reasons are mapped to readable text:
- Connection refused or timeout: `cannot reach http://host.docker.internal:11434 (is Ollama running?)`
- Model missing: `model 'llama3.2:3b' not found; run: ollama pull llama3.2:3b`
- HTTP 401/403: `provider rejected the API key (HTTP 401)`
- HTTP 429: `provider rate limit reached (HTTP 429)`
- Anything else: `unexpected response (HTTP 5xx)`

**Rationale**: Listing models costs no generation quota on free tiers. The 60-second TTL bounds probes to at most 60 per hour (SC-008), and a 3-second timeout keeps the health endpoint responsive.

**Alternatives considered**: Rejected in clarification Q3 (a real prompt per request; a check at startup only; no check).

## R8. SQLite, sqlite-vec and migrations (FR-005, US1 scenarios 3-4)

**Decision**:
- **Database file**: `DATA_DIR/knowledge.sqlite3`. `DATA_DIR` defaults to `./data` relative to the backend's working directory, and to `/data` in the container, which is backed by the named volume `app-data`.
- **Engine**: a SQLModel/SQLAlchemy engine with a `connect` event listener that calls `conn.enable_load_extension(True)`, `sqlite_vec.load(conn)` and `conn.enable_load_extension(False)` on every new connection. It also sets `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON`.
- **Startup sequence** (FastAPI lifespan):
  1. Create `DATA_DIR`, and fail with `data directory '<path>' is not writable` if a probe file cannot be written there.
  2. Run `alembic upgrade head` programmatically (`alembic.command.upgrade`), with `render_as_batch=True` for SQLite. This feature ships a baseline revision `0001_baseline` with no tables.
  3. Run the vector smoke check: `SELECT vec_version()` and a KNN query over an in-memory `vec0` virtual table with three 4-dimensional vectors, asserting that the nearest neighbour is the expected row.
  4. Record the result in application state for the health report.
  Any failure stops startup with a one-line reason. The app never half-runs (spec edge case).
- **Python runtime**: the container uses `python:3.12-slim`, whose `sqlite3` module supports `enable_load_extension`. Locally, uv's managed Python 3.12 also supports it. The smoke test runs in CI and inside the container (via quickstart), which covers both environments named in US1 scenario 3.

**Rationale**: Loading on every connection is the documented pattern for sqlite-vec with SQLAlchemy pools. Running migrations at startup gives "structure brought up to date automatically" and is idempotent across restarts (US1 scenario 4).

**Alternatives considered**: `SQLModel.metadata.create_all()`: cannot evolve existing data, which violates FR-005's "without losing existing data". A persistent smoke table: leaves test data in the user's store.

## R9. Health endpoint shape and refresh (FR-003, FR-004, US1 scenario 2)

**Decision**: `GET /api/health` returns `200` with a `HealthReport` (see [data-model.md](data-model.md) and [contracts/openapi-health.yaml](contracts/openapi-health.yaml)). The database section reports the startup self-check result; the endpoint does not re-query the database on every call, because startup already refuses to run without a working store. The frontend polls every 5 seconds with a 4-second timeout:
- `"Backend: healthy"` when the response is `200` and `status == "ok"`.
- `"Backend: unreachable"` on a network error, timeout, non-2xx response or unparsable body.
- The language model status shows as a separate secondary badge: `"LLM: <provider> · <model> — available"`, or `"LLM: … — unavailable (<reason>)"`.

**Rationale**: A 5-second poll plus a 4-second timeout keeps the worst case under the spec's 10 seconds even when requests hang rather than fail fast. SC-008's 70-second bound becomes 65 seconds, still within target.

**Alternatives considered**: Server-sent events for health: needless for a status badge. A 10-second poll: a hanging request could take up to 14 seconds to show "unreachable".

## R10. Frontend contract types and drift check (FR-016, FR-017, US3 scenarios 3-4)

**Decision**:
- `backend/scripts/export_openapi.py` writes `app.openapi()` to `frontend/src/api/openapi.json`, with sorted keys and a trailing newline so the output is stable.
- `openapi-typescript` (dev dependency) generates `frontend/src/api/schema.d.ts`.
- `npm run gen:api` runs both steps.
- The frontend uses `components["schemas"]["HealthReport"]` with a small `fetch` wrapper. No runtime client library is added.
- A new CI job, `contract`, sets up uv and Node, runs the generator, then runs `git diff --exit-code -- frontend/src/api`. On a difference it prints `API contract types are stale. Run: cd frontend && npm run gen:api, then commit the result.` and fails.

**Rationale**: The roadmap names openapi-typescript. Types-only generation is the smallest option that satisfies FR-016. Committing both the schema and the types makes drift visible in pull-request diffs.

**Alternatives considered**: `openapi-fetch` (another runtime dependency, not needed for one endpoint); `orval` or `openapi-generator` (heavier, and generate runtime code).

## R11. Testing approach without a real LLM (FR-014, FR-015, SC-004, SC-005)

**Decision**:
- **Backend**: an autouse fixture in `backend/tests/conftest.py`:
  - sets `LLM_PROVIDER=fake`;
  - points `DATA_DIR` at `tmp_path`;
  - replaces `socket.socket.connect` and `socket.create_connection` with a function that raises `NetworkBlockedError`. In-process `TestClient` traffic does not use sockets, so it keeps working.
- **Provider tests**: `OllamaProvider` and `OpenAICompatProvider` are tested with `httpx.MockTransport`, covering request shape, non-streaming and streaming parsing, error-to-reason mapping and key redaction.
- **Startup**: tests build the app with `create_app(settings)` and run its lifespan through `TestClient`.
- **Frontend**: Vitest with jsdom and `@testing-library/react`. The health-badge tests mock `fetch` and use fake timers.
- **CI**: runs `ruff check`, `pytest`, `npm run lint`, `npm test`, `npm run build` and the contract job.

**Rationale**: The socket guard proves US3 scenario 1 ("no test attempts a network call") mechanically, without adding a dependency such as pytest-socket. Fake timers make polling tests deterministic (SC-005).

**Alternatives considered**: `pytest-socket` (an extra dependency for about 10 lines of fixture); VCR-style cassettes (recorded HTTP is unnecessary when the transport can be mocked).

## R12. Development check command (FR-010)

**Decision**: `uv run python -m app.llm.check "Say hello in one sentence."` (inside the container: `docker compose exec backend python -m app.llm.check`). It builds the active provider from settings, prints `provider=<name> model=<model>`, then streams the reply to stdout. It exits 1 with the provider's reason on failure.

**Rationale**: One command exercises the configuration, the factory and both `complete`-style and streaming paths against a real model on demand. Tests never run it.

## R13. Default local model and ADR-001 spike (FR-019)

**Decision**: Spike script `backend/scripts/citation_spike.py`:
- It uses the provider abstraction (`LLM_PROVIDER=ollama`) and runs 5 fixed prompts against each candidate given on the command line.
- Each prompt supplies 3 numbered source passages and asks a question answerable from them.
- A reply counts as compliant when it contains at least one `[n]` marker and every marker refers to an existing source (1–3).
- It prints a table of compliance per model.

Candidates: two or three instruction-tuned models of 4B parameters or fewer that run on 8 GB RAM, chosen from the Ollama library at spike time, with `llama3.2:3b` (the current `.env.example` default) as the baseline. The results go into `docs/adr/001-local-model.md` (Context, Decision, Consequences, Alternatives), and the winning model becomes `OLLAMA_MODEL`'s default in both `Settings` and `.env.example`.

**Rationale**: The roadmap requires this spike. Model availability changes quickly, so the plan fixes the method and the measurement, not the model names.

## R14. Backend package layout cleanup

**Decision**: Keep the application package at `backend/app/`, as `main.py` already is. Remove the unused `uv init` artefacts: `backend/src/backend/`, `[project.scripts]` and `[build-system]`. Set `[tool.uv] package = false`, and add `[tool.pytest.ini_options] pythonpath = ["."]` with `testpaths = ["tests"]`. Ruff config: `target-version = "py312"`, rules `E,F,I,UP,B`.

**Rationale**: There are currently two competing package roots, which confuses imports and Docker builds (Constitution XI).

## R15. Container images

**Decision**:
- **Backend image**: `python:3.12-slim` with uv copied from `ghcr.io/astral-sh/uv`. It runs `uv sync --frozen --no-dev` in a cached dependency layer before copying the source. Command: `uv run --no-sync python -m app`. Docker `HEALTHCHECK` uses Python's `urllib` against `/api/health`.
- **Frontend image**: `node:26-slim`, matching the local Node 26 LTS. It runs `npm ci` and `npm run build`. Command: `npm run preview -- --host 0.0.0.0 --port 5173`.
- **Ignore files**: `.dockerignore` files exclude `.venv`, `node_modules`, `data` and `.env`.

**Risk**: the backend already depends on large packages for later features (`pymupdf`, `fastembed` with `onnxruntime`). The first image build may take several minutes and is the main threat to SC-001's 10 minutes. Mitigation: the dependency layer is cached separately, and the first build time is measured during quickstart validation. If it exceeds about 6 minutes, the fallback is to move the not-yet-used dependencies out until their features need them.
