"""Permisos mínimos del rol de ejecución `svc_app` (sin DDL).

El rol se crea fuera de las migraciones (`python -m app.db_admin bootstrap-role`) porque
su contraseña es un secreto. Si el rol no existe todavía, esta migración no hace nada y
basta con volver a ejecutar `migrate` después de crearlo.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE = "svc_app"


def upgrade() -> None:
    op.execute(  # ROLE es una constante del módulo
        f"""
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
            REVOKE ALL ON SCHEMA app FROM {ROLE};
            GRANT USAGE ON SCHEMA app TO {ROLE};
            GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA app TO {ROLE};
            -- DELETE solo en tablas de datos efímeros (limpieza).
            GRANT DELETE ON app.refresh_tokens, app.login_challenges, app.enrollment_codes
              TO {ROLE};
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO {ROLE};
            REVOKE ALL ON app.alembic_version FROM {ROLE};
            -- Las tablas que creen migraciones futuras heredan los mismos permisos.
            ALTER DEFAULT PRIVILEGES IN SCHEMA app
              GRANT SELECT, INSERT, UPDATE ON TABLES TO {ROLE};
            ALTER DEFAULT PRIVILEGES IN SCHEMA app
              GRANT USAGE, SELECT ON SEQUENCES TO {ROLE};
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(  # ROLE es una constante del módulo
        f"""
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
            REVOKE ALL ON ALL TABLES IN SCHEMA app FROM {ROLE};
            REVOKE ALL ON ALL SEQUENCES IN SCHEMA app FROM {ROLE};
            REVOKE ALL ON SCHEMA app FROM {ROLE};
          END IF;
        END
        $$;
        """
    )
