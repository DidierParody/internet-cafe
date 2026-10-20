"""Tareas de administración de la base de datos que se ejecutan con el rol owner.

- `bootstrap_app_role`: crea (o actualiza) el rol de ejecución de la API, sin DDL.
- `run_migrations`: aplica las migraciones de Alembic.

Uso por consola:
    uv run python -m app.db_admin bootstrap-role   # lee APP_DB_PASSWORD
    uv run python -m app.db_admin migrate
"""

import asyncio
import os
import re
import sys
from pathlib import Path

import asyncpg  # type: ignore[import-untyped]
from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def _asyncpg_dsn(url: str) -> tuple[str, dict[str, object]]:
    """DSN para asyncpg (sin sslmode/channel_binding) y opciones de TLS verificadas."""
    from app.core.db import requires_tls, tls_context, to_async_url

    dsn = to_async_url(url).replace("postgresql+asyncpg://", "postgresql://", 1)
    return dsn, ({"ssl": tls_context()} if requires_tls(url) else {})


async def _bootstrap(owner_url: str, role: str, password: str) -> None:
    if not _ROLE_RE.match(role):
        raise ValueError("Nombre de rol inválido")
    literal = "'" + password.replace("'", "''") + "'"
    dsn, opts = _asyncpg_dsn(owner_url)
    conn = await asyncpg.connect(dsn, **opts)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", role)
        verb = "ALTER" if exists else "CREATE"
        await conn.execute(
            f"{verb} ROLE {role} WITH LOGIN NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD {literal}"
        )
        await conn.execute(f"ALTER ROLE {role} SET statement_timeout = '15s'")
        await conn.execute(f"ALTER ROLE {role} SET idle_in_transaction_session_timeout = '30s'")
        await conn.execute(f"ALTER ROLE {role} SET search_path = app")
        # Si el esquema ya existe (migraciones previas), se reaplican los permisos.
        if await conn.fetchval("SELECT 1 FROM pg_namespace WHERE nspname = 'app'"):
            await conn.execute(_grants_sql(role))
    finally:
        await conn.close()


def _grants_sql(role: str) -> str:
    # `role` se valida con _ROLE_RE antes de llegar aquí.
    return f"""
        GRANT USAGE ON SCHEMA app TO {role};
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA app TO {role};
        GRANT DELETE ON app.refresh_tokens, app.login_challenges, app.enrollment_codes TO {role};
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO {role};
        REVOKE ALL ON app.alembic_version FROM {role};
    """


def bootstrap_app_role(owner_url: str, role: str, password: str) -> None:
    asyncio.run(_bootstrap(owner_url, role, password))


def run_migrations(owner_url: str, revision: str = "head") -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.attributes["url"] = owner_url
    cfg.attributes["skip_logging"] = True
    command.upgrade(cfg, revision)


def _main(argv: list[str]) -> int:
    from app.core.config import get_settings

    settings = get_settings()
    owner_url = settings.database_url_migrations
    if not owner_url:
        print("Falta DATABASE_URL_MIGRATIONS", file=sys.stderr)  # noqa: T201
        return 2
    if argv[:1] == ["bootstrap-role"]:
        password = os.environ.get("APP_DB_PASSWORD") or settings.app_db_password
        if not password:
            print("Falta APP_DB_PASSWORD", file=sys.stderr)  # noqa: T201
            return 2
        bootstrap_app_role(owner_url, "svc_app", password)
        print("Rol svc_app listo")  # noqa: T201
        return 0
    if argv[:1] == ["migrate"]:
        run_migrations(owner_url)
        print("Migraciones aplicadas")  # noqa: T201
        return 0
    print(__doc__)  # noqa: T201
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
