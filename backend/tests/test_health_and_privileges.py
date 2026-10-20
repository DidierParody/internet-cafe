import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.db import to_async_url


async def test_healthz_does_not_need_database(client: AsyncClient) -> None:
    response = await client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz_checks_database(client: AsyncClient) -> None:
    response = await client.get("/api/v1/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_migrations_create_core_tables(owner_engine: object) -> None:
    async with owner_engine.connect() as conn:  # type: ignore[attr-defined]
        tables = set(
            (
                await conn.execute(
                    sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'app'")
                )
            ).scalars()
        )
    assert {
        "users",
        "refresh_tokens",
        "labs",
        "machines",
        "enrollment_codes",
        "login_challenges",
        "access_sessions",
        "audit_log",
    } <= tables


@pytest.fixture
async def app_role_conn(database_urls: tuple[str, str]):  # type: ignore[no-untyped-def]
    engine = create_async_engine(to_async_url(database_urls[1]))
    async with engine.connect() as conn:
        yield conn
    await engine.dispose()


async def test_app_role_cannot_create_tables(app_role_conn) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(DBAPIError, match="permission denied"):
        await app_role_conn.execute(sa.text("CREATE TABLE app.intruso (id int)"))


async def test_app_role_cannot_delete_users(app_role_conn) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(DBAPIError, match="permission denied"):
        await app_role_conn.execute(sa.text("DELETE FROM app.users"))
