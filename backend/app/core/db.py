"""Conexión a PostgreSQL con SQLAlchemy async + asyncpg."""

import ssl
import uuid
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_TLS_MODES = {"require", "verify-ca", "verify-full"}


def to_async_url(url: str) -> str:
    """Convierte una URL de libpq (como la de Neon) al formato de SQLAlchemy + asyncpg.

    asyncpg no entiende `sslmode` ni `channel_binding`: se quitan de la URL y el TLS se
    configura en `connect_args` (ver `connect_args`).
    """
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.pop("sslmode", None)
    query.pop("channel_binding", None)
    return urlunsplit(("postgresql+asyncpg", parts.netloc, parts.path, urlencode(query), ""))


def requires_tls(url: str) -> bool:
    return dict(parse_qsl(urlsplit(url).query)).get("sslmode") in _TLS_MODES


def tls_context() -> ssl.SSLContext:
    """TLS con verificación del certificado y del nombre del servidor (CA del sistema)."""
    return ssl.create_default_context()


def connect_args(url: str) -> dict[str, Any]:
    args: dict[str, Any] = {
        # Compatible con PgBouncer (endpoint "-pooler" de Neon) en modo transacción.
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
    }
    if requires_tls(url):
        args["ssl"] = tls_context()
    return args


def create_engine(url: str, **kwargs: Any) -> AsyncEngine:
    pooled = {"pool_size": 5, "max_overflow": 5, "pool_pre_ping": True, "pool_recycle": 300}
    options: dict[str, Any] = {} if "poolclass" in kwargs else pooled
    options.update(kwargs)
    return create_async_engine(to_async_url(url), connect_args=connect_args(url), **options)


class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url)
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def dispose(self) -> None:
        await self.engine.dispose()


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.db
    async with database.sessionmaker() as session:
        yield session
