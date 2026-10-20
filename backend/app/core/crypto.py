"""Cifrado de datos personales (AES-256-GCM) y blind indexes (HMAC-SHA256).

Formato del ciphertext: b"v1" + nonce (12 bytes) + ciphertext con tag.
"""

import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

_VERSION = b"v1"


class DecryptionError(Exception):
    pass


def encrypt(plaintext: str, *, aad: str) -> bytes:
    nonce = os.urandom(12)
    ct = AESGCM(get_settings().enc_key).encrypt(nonce, plaintext.encode(), aad.encode())
    return _VERSION + nonce + ct


def decrypt(blob: bytes, *, aad: str) -> str:
    if blob[:2] != _VERSION:
        raise DecryptionError("Versión de cifrado desconocida")
    nonce, ct = blob[2:14], blob[14:]
    try:
        return AESGCM(get_settings().enc_key).decrypt(nonce, ct, aad.encode()).decode()
    except InvalidTag as exc:
        raise DecryptionError("No se pudo descifrar el dato") from exc


def normalize(value: str) -> str:
    return value.strip().lower()


def blind_index(value: str) -> bytes:
    return hmac.new(get_settings().bidx_key, normalize(value).encode(), hashlib.sha256).digest()


def mask_code(code: str) -> str:
    if len(code) >= 7:
        return code[:4] + "*" * (len(code) - 6) + code[-2:]
    if len(code) >= 3:
        return code[0] + "*" * (len(code) - 2) + code[-1]
    return "*" * len(code)
