FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.10 /uv /bin/uv

# Use the image's Python, compile bytecode once at build time, and copy (not link)
# packages out of uv's cache mount.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Dependencies first, in their own layer: source edits do not reinstall them (R15).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

# A named volume mounted at /data starts with this directory's owner, so the
# unprivileged user can write the database there.
RUN useradd --create-home --uid 1000 app \
    && mkdir /data \
    && chown app:app /data
USER app

ENV DATA_DIR=/data

EXPOSE 8000

# A short interval keeps "depends_on: service_healthy" from delaying the UI by
# Docker's 30 s default (SC-002).
HEALTHCHECK --interval=5s --timeout=4s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=3)"]

CMD ["uv", "run", "--no-sync", "python", "-m", "app"]
