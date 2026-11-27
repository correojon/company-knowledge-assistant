# company-knowledge-assistant

An AI assistant that answers questions from your company's documents. It runs locally, at no cost.

## Prerequisites

- Git.
- Docker with Compose v2.24 or newer. Check with `docker compose version`.
- For native runs and tests only: [uv](https://docs.astral.sh/uv/) and Node 26.

## Getting started

```bash
git clone <repo-url> company-knowledge-assistant
cd company-knowledge-assistant
cp .env.example .env        # optional: built-in defaults apply without it
docker compose up --build
```

Open http://localhost:5173. The app shell appears, and the badge reads **Backend: healthy** once the backend is ready.

The first build downloads the base images and dependencies, so it takes a few minutes. Later starts are faster.

Stop the app with `Ctrl+C`, or `docker compose down`. Your data is kept in the `app-data` volume between runs.

## Configuration

All settings live in `.env`, and [.env.example](.env.example) explains each one. If you skip the copy step, the backend logs a "no .env file found; using built-in defaults" notice and starts anyway.

After editing `.env`, restart the stack with `docker compose up -d`.

## Troubleshooting

### Port 5173 or 8000 is already in use

Another program on your machine is using the port. Depending on your system, you see one of two symptoms:

- **Linux or macOS:** `docker compose up` fails with `port is already allocated`.
- **WSL2 with Docker Desktop:** the stack starts without an error, but http://localhost:5173 shows the other program instead of the app. Docker Desktop cannot see programs that listen inside WSL.

In both cases, pick a free port in `.env`, then run `docker compose up` again:

```bash
FRONTEND_PORT=5174    # the app is then at http://localhost:5174
BACKEND_PORT=8001     # if port 8000 is the one in use
```

## Running without Docker

Run the backend and the frontend in two terminals, from the repository root. The backend reads the `.env` at the repository root.

```bash
# Terminal 1: backend on http://localhost:8000
cd backend && uv run python -m app
```

```bash
# Terminal 2: frontend on http://localhost:5173
cd frontend && npm ci && npm run dev
```

`FRONTEND_PORT` and `BACKEND_PORT` apply only to Docker. The frontend sends `/api` requests to `API_PROXY_TARGET` (default `http://localhost:8000`).

## Tests

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm test && npm run lint && npm run build
```

No language model is needed to run the tests.
