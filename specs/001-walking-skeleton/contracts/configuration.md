# Contract: Configuration and commands

## Environment variables

`.env.example` MUST list every key below, in this order and with these defaults. The backend `Settings` class MUST use the same defaults; a unit test enforces this parity (FR-008, clarification Q2).

| Key | Default | Read by | Meaning |
|---|---|---|---|
| `CONFIG_FILE_LOADED` | `true` in the example file (absent means `false`) | backend | Sentinel. Keep this line. When it is absent, the backend prints a "no .env file found" notice |
| `LLM_PROVIDER` | `ollama` | backend | `fake` (canned replies) \| `ollama` (local model) \| `openai_compat` (free hosted model) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | backend | Local runs. Compose overrides it to `http://host.docker.internal:11434`, or to `http://ollama:11434` with `compose.ollama.yml` |
| `OLLAMA_MODEL` | `llama3.2:3b` (final value set by ADR-001) | backend, `ollama-pull` | Local model name |
| `OPENAI_COMPAT_BASE_URL` | *(empty)* | backend | For example `https://api.groq.com/openai/v1`. Required for `openai_compat` |
| `OPENAI_COMPAT_API_KEY` | *(empty)* | backend | Required for `openai_compat`. Never committed or logged |
| `OPENAI_COMPAT_MODEL` | *(empty)* | backend | Required for `openai_compat` |
| `LLM_TIMEOUT_SECONDS` | `120` | backend | Generation timeout |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | backend (from Feature 003) | Embedding model |
| `DATA_DIR` | `./data` | backend | Compose overrides it to `/data` (named volume `app-data`) |
| `BACKEND_PORT` | `8000` | compose only | Host port for the backend |
| `FRONTEND_PORT` | `5173` | compose only | Host port for the web interface |
| `API_PROXY_TARGET` | `http://localhost:8000` | frontend (Vite) only | Where `/api` is proxied. Compose sets `http://backend:8000` |

## Startup errors (exit codes and messages)

| Condition | Exit code | Message shape |
|---|---|---|
| `LLM_PROVIDER` empty or unknown | 2 | `Invalid configuration: LLM_PROVIDER='<value>' is not allowed. Allowed values: fake, ollama, openai_compat.` |
| `openai_compat` with a missing field | 2 | `Invalid configuration: OPENAI_COMPAT_API_KEY is required when LLM_PROVIDER=openai_compat.` (one line per missing field) |
| Invalid URL | 2 | `Invalid configuration: OLLAMA_BASE_URL='<value>' is not a valid http(s) URL.` |
| Data directory not writable | 1 | `Startup failed: data directory '<path>' is not writable.` |
| Migration to head fails | 1 | `Startup failed: migration failed: <reason>.` |
| sqlite-vec cannot load or the smoke query fails | 1 | `Startup failed: vector search unavailable: <reason>.` |

## Commands

| Purpose | Command (from repository root unless noted) |
|---|---|
| Start everything (default) | `docker compose up --build` |
| Start with a bundled local model | `docker compose -f compose.yml -f compose.ollama.yml up --build` |
| Run the backend natively | `cd backend && uv run python -m app` |
| Run the frontend natively | `cd frontend && npm run dev` |
| Dev check of the active provider | `cd backend && uv run python -m app.llm.check "Say hello"` (container: `docker compose exec backend uv run --no-sync python -m app.llm.check "Say hello"`) |
| Backend tests and lint | `cd backend && uv run pytest && uv run ruff check .` |
| Frontend tests, lint and build | `cd frontend && npm test && npm run lint && npm run build` |
| Regenerate API types | `cd frontend && npm run gen:api` |
| Model citation spike (ADR-001) | `cd backend && uv run python scripts/citation_spike.py <model> [<model> ...]` |
