"""Exporta el contrato OpenAPI de la API a un archivo JSON.

Uso: `uv run python -m app.openapi_export ../contracts/openapi.json`

El frontend genera sus tipos a partir de ese archivo (`npm run gen:api`).
"""

import json
import sys
from pathlib import Path

from app.main import create_app


def main(target: str) -> None:
    schema = create_app().openapi()
    Path(target).write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../contracts/openapi.json")
