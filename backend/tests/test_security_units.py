import time
from datetime import timedelta

import jwt
import pytest

from app.core import crypto, ids, passwords, tokens


def test_uuid7_has_version_7_and_is_time_ordered() -> None:
    first = ids.uuid7()
    time.sleep(0.002)
    second = ids.uuid7()
    assert first.version == 7
    assert second.version == 7
    assert first < second


def test_encrypt_roundtrip_uses_random_nonce() -> None:
    a = crypto.encrypt("ana@uni.edu.co", aad="users.email")
    b = crypto.encrypt("ana@uni.edu.co", aad="users.email")
    assert a != b
    assert crypto.decrypt(a, aad="users.email") == "ana@uni.edu.co"


def test_decrypt_with_other_aad_fails() -> None:
    blob = crypto.encrypt("2021001234", aad="users.student_code")
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(blob, aad="users.full_name")


def test_blind_index_is_deterministic_and_normalized() -> None:
    assert crypto.blind_index(" Ana@Uni.EDU.co ") == crypto.blind_index("ana@uni.edu.co")
    assert crypto.blind_index("ana@uni.edu.co") != crypto.blind_index("eva@uni.edu.co")
    assert len(crypto.blind_index("x")) == 32


def test_password_hash_and_verify() -> None:
    hashed = passwords.hash_password("Contraseña-Segura-1")
    assert hashed.startswith("$argon2id$")
    assert passwords.verify_password("Contraseña-Segura-1", hashed)
    assert not passwords.verify_password("otra-cosa-123", hashed)


def test_access_token_roundtrip() -> None:
    token = tokens.issue_access_token(subject="0192-abc", role="student")
    claims = tokens.decode_access_token(token)
    assert claims["sub"] == "0192-abc"
    assert claims["role"] == "student"
    assert jwt.get_unverified_header(token)["alg"] == "ES256"


def test_expired_access_token_is_rejected() -> None:
    token = tokens.issue_access_token(subject="u", role="student", ttl=timedelta(seconds=-1))
    with pytest.raises(tokens.InvalidTokenError):
        tokens.decode_access_token(token)


def test_opaque_token_hash_is_stable_sha256() -> None:
    value = tokens.new_opaque_token()
    assert len(value) >= 43
    assert tokens.hash_token(value) == tokens.hash_token(value)
    assert len(tokens.hash_token(value)) == 32


def test_mask_student_code() -> None:
    assert crypto.mask_code("2021001234") == "2021****34"
    assert crypto.mask_code("12345") == "1***5"
