"""Entorno de Alembic. Las migraciones se ejecutan con el rol owner (DDL), nunca con el de la app.

URL: `config.attributes["url"]` (uso programático) o DATABASE_URL_MIGRATIONS.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection

from app.core.db import create_engine
from app.models import SCHEMA, Base

config = context.config
if config.config_file_name is not None and not config.attributes.get("skip_logging"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    url = config.attributes.get("url") or os.environ.get("DATABASE_URL_MIGRATIONS")
    if not url:
        from app.core.config import get_settings

        url = get_settings().database_url_migrations
    if not url:
        raise RuntimeError("Falta DATABASE_URL_MIGRATIONS (credencial owner para migrar)")
    return str(url)


def do_run_migrations(connection: Connection) -> None:
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=SCHEMA,
        include_name=lambda name, type_, _parent: type_ != "schema" or name == SCHEMA,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Solo se soporta el modo online")
asyncio.run(run_async_migrations())
