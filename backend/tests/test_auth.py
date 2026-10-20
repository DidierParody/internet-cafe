from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core import crypto
from tests.helpers import DEFAULT_PASSWORD, bearer, login, register, student_token

REFRESH_COOKIE = "__Secure-rt"


def _use_refresh(client: AsyncClient, value: str | None) -> None:
    """Deja en el cookie jar solo el refresh token indicado."""
    assert value is not None
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, value, domain="testserver.local", path="/api/v1/auth")


async def _count_users(engine: AsyncEngine) -> int:
    async with engine.connect() as conn:
        return int((await conn.execute(sa.text("SELECT count(*) FROM app.users"))).scalar_one())


async def test_register_creates_active_user_with_encrypted_pii(
    client: AsyncClient, owner_engine: AsyncEngine
) -> None:
    await register(client)
    async with owner_engine.connect() as conn:
        row = (
            await conn.execute(
                sa.text("SELECT email_ct, email_bidx, full_name_ct, status FROM app.users")
            )
        ).one()
    assert b"ana@uni.edu.co" not in row.email_ct
    assert row.email_bidx == crypto.blind_index("ana@uni.edu.co")
    assert crypto.decrypt(row.full_name_ct, aad="users.full_name") == "Ana Pérez"
    assert row.status == "active"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "ana@gmail.com"),
        ("password", "corta"),
        ("privacy_consent", False),
        ("student_code", ""),
    ],
)
async def test_register_rejects_invalid_data(
    client: AsyncClient, field: str, value: object
) -> None:
    payload = {
        "email": "ana@uni.edu.co",
        "student_code": "2021001234",
        "full_name": "Ana Pérez",
        "password": DEFAULT_PASSWORD,
        "privacy_consent": True,
        field: value,
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_register_duplicate_is_silent(client: AsyncClient, owner_engine: AsyncEngine) -> None:
    await register(client)
    await register(client, code="2021009999")
    await register(client, email="otra@uni.edu.co")  # mismo código estudiantil
    assert await _count_users(owner_engine) == 1


async def test_login_returns_token_and_secure_refresh_cookie(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "ANA@uni.edu.co ", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["user"]["full_name"] == "Ana Pérez"
    assert body["user"]["role"] == "student"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{REFRESH_COOKIE}=")
    for attribute in ("HttpOnly", "Secure", "SameSite=strict", "Path=/api/v1/auth"):
        assert attribute.lower() in cookie.lower()


@pytest.mark.parametrize("email", ["ana@uni.edu.co", "nadie@uni.edu.co"])
async def test_login_invalid_credentials_are_indistinguishable(
    client: AsyncClient, email: str
) -> None:
    await register(client)
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": "x" * 12})
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


async def test_account_locks_after_five_failures(client: AsyncClient) -> None:
    await register(client)
    for _ in range(5):
        await client.post(
            "/api/v1/auth/login", json={"email": "ana@uni.edu.co", "password": "mala-clave-1"}
        )
    response = await client.post(
        "/api/v1/auth/login", json={"email": "ana@uni.edu.co", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 423
    assert response.json()["code"] == "AUTH_ACCOUNT_LOCKED"


async def test_me_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me")
    assert response.status_code == 401
    bad = await client.get("/api/v1/me", headers=bearer("no-es-un-jwt"))
    assert bad.status_code == 401
    assert bad.json()["code"] == "AUTH_TOKEN_EXPIRED"


async def test_me_returns_profile_with_masked_code(client: AsyncClient) -> None:
    token = await student_token(client)
    response = await client.get("/api/v1/me", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ana@uni.edu.co"
    assert body["student_code_masked"] == "2021****34"
    assert "student_code" not in body


async def test_refresh_rotates_cookie(client: AsyncClient) -> None:
    await register(client)
    await login(client)
    first_cookie = client.cookies.get(REFRESH_COOKIE)
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert client.cookies.get(REFRESH_COOKIE) != first_cookie


async def test_refresh_rejects_foreign_origin(client: AsyncClient) -> None:
    await register(client)
    await login(client)
    response = await client.post("/api/v1/auth/refresh", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


async def test_refresh_reuse_within_grace_is_allowed(client: AsyncClient) -> None:
    await register(client)
    await login(client)
    old = client.cookies.get(REFRESH_COOKIE)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200
    _use_refresh(client, old)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200


async def test_refresh_reuse_after_grace_revokes_family(
    client: AsyncClient, owner_engine: AsyncEngine
) -> None:
    await register(client)
    await login(client)
    old = client.cookies.get(REFRESH_COOKIE)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200
    newest = client.cookies.get(REFRESH_COOKIE)
    async with owner_engine.begin() as conn:
        await conn.execute(
            sa.text("UPDATE app.refresh_tokens SET revoked_at = :t WHERE revoked_at IS NOT NULL"),
            {"t": datetime.now(UTC) - timedelta(seconds=60)},
        )
    _use_refresh(client, old)
    reuse = await client.post("/api/v1/auth/refresh")
    assert reuse.status_code == 401
    _use_refresh(client, newest)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_logout_revokes_refresh(client: AsyncClient) -> None:
    await register(client)
    await login(client)
    cookie = client.cookies.get(REFRESH_COOKIE)
    assert (await client.post("/api/v1/auth/logout")).status_code == 204
    _use_refresh(client, cookie)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_change_password_requires_current_one(client: AsyncClient) -> None:
    token = await student_token(client)
    wrong = await client.patch(
        "/api/v1/me/password",
        headers=bearer(token),
        json={"current_password": "no-es-la-clave", "new_password": "nueva-clave-segura"},
    )
    assert wrong.status_code == 401
    ok = await client.patch(
        "/api/v1/me/password",
        headers=bearer(token),
        json={"current_password": DEFAULT_PASSWORD, "new_password": "nueva-clave-segura"},
    )
    assert ok.status_code == 204
    await login(client, password="nueva-clave-segura")
