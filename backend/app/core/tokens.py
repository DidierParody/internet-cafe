"""Tokens: access JWT (ES256) y tokens opacos (refresh, reto QR, equipo, enrolamiento)."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey

from app.core.config import get_settings

ISSUER = "internet-cafe-api"
AUDIENCE = "web"


class InvalidTokenError(Exception):
    pass


@lru_cache
def _private_key() -> EllipticCurvePrivateKey:
    key = serialization.load_pem_private_key(get_settings().jwt_private_pem, password=None)
    if not isinstance(key, EllipticCurvePrivateKey):
        raise TypeError("JWT_PRIVATE_KEY_B64 debe ser una llave EC P-256")
    return key


def issue_access_token(*, subject: str, role: str, ttl: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    lifetime = ttl if ttl is not None else timedelta(seconds=get_settings().access_token_ttl_s)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + lifetime,
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(claims, _private_key(), algorithm="ES256")


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            _private_key().public_key(),
            algorithms=["ES256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()
