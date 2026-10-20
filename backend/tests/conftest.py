"""Configuración de pruebas.

Las variables de entorno se fijan antes de importar la app. La base de datos es un
PostgreSQL 18 en Docker (la misma versión que Neon) levantado con testcontainers: las
migraciones corren con el superusuario (como en producción con el owner) y la API se
conecta con el rol `svc_app`.
"""

import base64
import os
import secrets
from collections.abc import AsyncIterator, Iterator
from concurrent.futures import ThreadPoolExecutor

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _pem_b64() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return base64.b64encode(pem).decode()


os.environ.update(
    {
        "DATABASE_URL": "postgresql://placeholder@localhost/placeholder",
        "DATA_ENC_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
        "BLIND_INDEX_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
        "JWT_PRIVATE_KEY_B64": _pem_b64(),
        "FRONTEND_BASE_URL": "https://front.example",
        "ALLOWED_EMAIL_DOMAINS": "uni.edu.co",
        "RUN_BACKGROUND_JOBS": "false",
    }
)

import pytest  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine  # noqa: E402

SVC_PASSWORD = "svc-app-test-password"


@pytest.fixture(scope="session")
def database_urls() -> Iterator[tuple[str, str]]:
    """Levanta Postgres, crea el rol de la app y aplica las migraciones."""
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:18-alpine", driver=None) as pg:
        owner_url = pg.get_connection_url()  # postgresql://test:test@host:port/test
        app_url = owner_url.replace("test:test@", f"svc_app:{SVC_PASSWORD}@", 1)

        from app.db_admin import bootstrap_app_role, run_migrations

        # Usan asyncio.run: se ejecutan en otro hilo para no chocar con el loop de pytest.
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(bootstrap_app_role, owner_url, "svc_app", SVC_PASSWORD).result()
            pool.submit(run_migrations, owner_url).result()
        yield owner_url, app_url


@pytest.fixture(scope="session")
async def owner_engine(database_urls: tuple[str, str]) -> AsyncIterator[AsyncEngine]:
    from app.core.db import to_async_url

    engine = create_async_engine(to_async_url(database_urls[0]))
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def app(database_urls: tuple[str, str]) -> AsyncIterator[object]:
    os.environ["DATABASE_URL"] = database_urls[1]
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    application = create_app()
    yield application
    await application.state.db.dispose()


@pytest.fixture
async def clean_db(owner_engine: AsyncEngine) -> None:
    """Vacía las tablas del esquema `app` antes de la prueba."""
    async with owner_engine.begin() as conn:
        tables = (
            (
                await conn.execute(
                    sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'app'")
                )
            )
            .scalars()
            .all()
        )
        names = [t for t in tables if t != "alembic_version"]
        if names:
            await conn.execute(
                sa.text(
                    "TRUNCATE " + ", ".join(f"app.{n}" for n in names) + " RESTART IDENTITY CASCADE"
                )
            )


@pytest.fixture
async def client(app: object, clean_db: None) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(
        transport=transport,
        base_url="https://testserver",
        headers={"Origin": "https://front.example"},
    ) as c:
        yield c
