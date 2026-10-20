"""Genera las llaves de la API: `uv run python -m app.keys`.

Imprime líneas KEY=valor listas para el .env o el dashboard de Render.
"""

import base64
import secrets

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generate() -> dict[str, str]:
    pem = ec.generate_private_key(ec.SECP256R1()).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return {
        "DATA_ENC_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
        "BLIND_INDEX_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
        "JWT_PRIVATE_KEY_B64": base64.b64encode(pem).decode(),
        "APP_DB_PASSWORD": secrets.token_urlsafe(32),
    }


if __name__ == "__main__":
    for key, value in generate().items():
        print(f"{key}={value}")  # noqa: T201
