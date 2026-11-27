"""``python -m app``: load settings, prepare the store, then serve (FR-008).

Startup runs before uvicorn so a broken store ends with one readable line and exit
code 1, not a lifespan traceback (contracts/configuration.md "Startup errors").
"""

import sys

import uvicorn

from app.config import load_settings, startup_notice
from app.db import StartupError
from app.main import create_app, startup

HOST = "0.0.0.0"
PORT = 8000


def main() -> None:
    settings = load_settings()
    notice = startup_notice(settings)
    if notice is not None:
        print(notice, flush=True)

    try:
        state = startup(settings)
    except StartupError as exc:
        print(f"Startup failed: {str(exc).rstrip('.')}.", file=sys.stderr)
        sys.exit(1)

    try:
        uvicorn.run(create_app(settings, state=state), host=HOST, port=PORT)
    finally:
        state.engine.dispose()


if __name__ == "__main__":
    main()
