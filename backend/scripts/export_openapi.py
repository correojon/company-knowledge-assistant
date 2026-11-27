"""Write the backend's OpenAPI schema for the frontend's generated types (R10).

Usage, from backend/: ``uv run python scripts/export_openapi.py [OUTPUT]``. The default
output is frontend/src/api/openapi.json. The schema is built from fixed settings, never
from a local .env, so every machine exports the same bytes.
"""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = BACKEND_DIR.parent / "frontend" / "src" / "api" / "openapi.json"

# Running a file puts its own folder on sys.path, not backend/, where ``app`` lives.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    output = Path(args[0]) if args else DEFAULT_OUTPUT
    # The lifespan never runs: openapi() needs no database or provider.
    app = create_app(Settings(_env_file=None, llm_provider="fake"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
