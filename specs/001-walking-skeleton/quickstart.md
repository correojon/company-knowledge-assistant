# Quickstart and validation: Walking Skeleton (Feature 001)

This runbook proves each acceptance scenario end to end. Commands are listed in [contracts/configuration.md](contracts/configuration.md), and the health response shape is in [contracts/openapi-health.yaml](contracts/openapi-health.yaml).

## Prerequisites

- Git and Docker with Compose v2.24 or newer (needed for `env_file` with `required: false`).
- For native runs and tests: uv and Node 26.
- Optional: Ollama on the host, with the default model pulled (`ollama pull llama3.2:3b`). On Linux and WSL2 without Docker Desktop, start it with `OLLAMA_HOST=0.0.0.0:11434` so containers can reach it.

## V1. Fresh clone, one command (US1 scenarios 1, 3, 5; SC-001, SC-002)

```bash
cd "$(mktemp -d)" && git clone <repo-url> app && cd app
cp .env.example .env
time docker compose up --build        # note the first build time (R15 risk)
```

Expected:
- http://localhost:5173 shows the app shell with Documents, Search and Chat entries, each with a "not available yet" placeholder.
- The badge reads **Backend: healthy** within 60 seconds of the containers starting.
- `curl -s localhost:8000/api/health` returns `status: ok`, `database.vector_search: ok` and a non-empty `vector_search_version`.

## V2. No `.env` copied (US1 scenario 6)

Repeat V1 without `cp .env.example .env`. Expected: the backend log contains the "no .env file found; using built-in defaults" notice, and the UI shows **Backend: healthy**.

## V3. Restart keeps data (US1 scenario 4)

`docker compose down && docker compose up` (no `-v`). Expected: a clean start, `schema_revision` unchanged, and the log shows the migration as already at head.

## V4. Backend goes away (US1 scenario 2)

While the UI is open: `docker compose stop backend`. Expected: **Backend: unreachable** within 10 seconds. Then `docker compose start backend`, and the badge returns to healthy on its own.

## V5. Provider switching (US2; SC-003, SC-008)

| Step | Change in `.env`, then `docker compose up -d backend` | Expected health `llm` section |
|---|---|---|
| a | `LLM_PROVIDER=fake` | `provider: fake`, `status: available` |
| b | `LLM_PROVIDER=ollama` with host Ollama stopped | `status: unavailable`, reason mentions `is Ollama running?`. The backend badge is still healthy |
| c | Start host Ollama | Within 65 seconds the UI shows LLM available |
| d | `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=not-a-model` | `unavailable`, reason contains `ollama pull not-a-model` |
| e | `LLM_PROVIDER=openai_compat` with a free-tier base URL, model and key | `available` |
| f | `LLM_PROVIDER=openai_compat` with `OPENAI_COMPAT_API_KEY` empty | The backend exits. The log names `OPENAI_COMPAT_API_KEY` |
| g | `LLM_PROVIDER=banana` | The backend exits. The log lists `fake, ollama, openai_compat` |

For steps a, c and e, also run the dev check:
`docker compose exec backend uv run --no-sync python -m app.llm.check "Say hello"`. Expected: `provider=<name> model=<model>`, followed by a streamed reply (FR-010).

Secret check (FR-013): after step e, `docker compose logs backend | grep -c "<first 8 chars of key>"` prints `0`, and the health JSON does not contain the key.

## V6. Bundled local model (FR-007)

```bash
docker compose -f compose.yml -f compose.ollama.yml up --build
```

Expected: `ollama-pull` downloads `OLLAMA_MODEL` and exits 0, and health then shows the ollama provider `available` at `http://ollama:11434`. The plain `docker compose up` from V1 never started an `ollama` container (`docker compose ps` lists only `backend` and `frontend`).

## V7. Tests without a model (US3; SC-004, SC-005)

```bash
# with Ollama stopped and LLM_PROVIDER=ollama in .env, to prove tests ignore it
cd backend && time uv run pytest && uv run ruff check .
for i in $(seq 10); do uv run pytest -q -p no:cacheprovider || break; done
cd ../frontend && npm test && npm run lint && npm run build
```

Expected: everything passes. The backend suite finishes in under 2 minutes, all 10 runs pass, and the socket guard reports no blocked connection attempts.

## V8. Contract drift fails CI (US3 scenarios 3-4; SC-006)

On a scratch branch, add an optional field to `HealthReport` without running `npm run gen:api`, then push. Expected: the CI `contract` job fails with "API contract types are stale". Run `npm run gen:api`, commit and push: the job passes.

## V9. Port in use (edge case)

Occupy port 5173 (`python3 -m http.server 5173`), make sure the stack is down (`docker compose down`), then run `docker compose up`. Expected, depending on the host:

- Native Linux or macOS: Docker reports that the port is already allocated, and the frontend does not start.
- WSL2 with Docker Desktop: Docker publishes the port outside the WSL network, so it does not see the clash. The stack starts, but `curl -s -o /dev/null -w "%{http_code}\n" localhost:5173/api/health` from WSL reaches the other program (here `404`), not the app.

In both cases, setting `FRONTEND_PORT=5174` in `.env` fixes it, and the README says so and describes both symptoms.

## V10. Secrets never committed (SC-007)

`git log -p | grep -iE "api[_-]?key\s*=\s*\S{8,}"` prints nothing, and `git check-ignore .env` confirms that `.env` is ignored.
