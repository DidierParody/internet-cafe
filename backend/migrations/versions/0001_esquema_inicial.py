"""Esquema inicial del PoC (sección 11 del SRS).

Revision ID: 0001
Revises:
Create Date: 2026-10-20 11:07:09.791004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "actor_type",
            sa.Enum("user", "machine", "system", name="audit_actor_type", schema="app"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
        schema="app",
    )
    op.create_index(
        op.f("ix_audit_log_action"), "audit_log", ["action"], unique=False, schema="app"
    )
    op.create_index(
        op.f("ix_audit_log_created_at"), "audit_log", ["created_at"], unique=False, schema="app"
    )
    op.create_table(
        "labs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("building", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_labs")),
        sa.UniqueConstraint("name", name=op.f("uq_labs_name")),
        schema="app",
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email_ct", sa.LargeBinary(), nullable=False),
        sa.Column("email_bidx", sa.LargeBinary(), nullable=False),
        sa.Column("student_code_ct", sa.LargeBinary(), nullable=True),
        sa.Column("student_code_bidx", sa.LargeBinary(), nullable=True),
        sa.Column("full_name_ct", sa.LargeBinary(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "role", sa.Enum("student", "admin", name="user_role", schema="app"), nullable=False
        ),
        sa.Column(
            "status",
            sa.Enum("pending_verification", "active", "blocked", name="user_status", schema="app"),
            nullable=False,
        ),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("privacy_consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "failed_login_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email_bidx", name=op.f("uq_users_email_bidx")),
        sa.UniqueConstraint("student_code_bidx", name=op.f("uq_users_student_code_bidx")),
        schema="app",
    )
    op.create_table(
        "machines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lab_id", sa.UUID(), nullable=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("hostname", sa.String(length=63), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending_enrollment", "active", "disabled", name="machine_status", schema="app"
            ),
            nullable=False,
        ),
        sa.Column(
            "mode", sa.Enum("passive", "kiosk", name="machine_mode", schema="app"), nullable=False
        ),
        sa.Column("api_token_hash", sa.LargeBinary(), nullable=True),
        sa.Column("public_key_jwk", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("key_thumbprint", sa.String(length=64), nullable=True),
        sa.Column("app_version", sa.String(length=20), nullable=True),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lab_id"], ["app.labs.id"], name=op.f("fk_machines_lab_id_labs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_machines")),
        sa.UniqueConstraint("api_token_hash", name=op.f("uq_machines_api_token_hash")),
        sa.UniqueConstraint("code", name=op.f("uq_machines_code")),
        sa.UniqueConstraint("key_thumbprint", name=op.f("uq_machines_key_thumbprint")),
        schema="app",
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.UUID(), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by"],
            ["app.refresh_tokens.id"],
            name=op.f("fk_refresh_tokens_replaced_by_refresh_tokens"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app.users.id"], name=op.f("fk_refresh_tokens_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
        schema="app",
    )
    op.create_index(
        op.f("ix_refresh_tokens_family_id"),
        "refresh_tokens",
        ["family_id"],
        unique=False,
        schema="app",
    )
    op.create_index(
        op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False, schema="app"
    )
    op.create_table(
        "enrollment_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("machine_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.LargeBinary(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["app.users.id"], name=op.f("fk_enrollment_codes_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["app.machines.id"],
            name=op.f("fk_enrollment_codes_machine_id_machines"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enrollment_codes")),
        sa.UniqueConstraint("code_hash", name=op.f("uq_enrollment_codes_code_hash")),
        schema="app",
    )
    op.create_table(
        "login_challenges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("machine_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "approved", "expired", "cancelled", name="challenge_status", schema="app"
            ),
            nullable=False,
        ),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["app.users.id"], name=op.f("fk_login_challenges_approved_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["app.machines.id"],
            name=op.f("fk_login_challenges_machine_id_machines"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_challenges")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_login_challenges_token_hash")),
        schema="app",
    )
    op.create_index(
        op.f("ix_login_challenges_machine_id_created_at"),
        "login_challenges",
        ["machine_id", "created_at"],
        unique=False,
        schema="app",
    )
    op.create_table(
        "access_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("machine_id", sa.UUID(), nullable=False),
        sa.Column("challenge_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "end_reason",
            sa.Enum(
                "user_logout_pc",
                "user_logout_web",
                "superseded",
                "heartbeat_timeout",
                "admin_forced",
                "machine_shutdown",
                name="session_end_reason",
                schema="app",
            ),
            nullable=True,
        ),
        sa.CheckConstraint(
            "(ended_at IS NULL) = (end_reason IS NULL)",
            name=op.f("ck_access_sessions_end_consistent"),
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name=op.f("ck_access_sessions_end_after_start"),
        ),
        sa.ForeignKeyConstraint(
            ["challenge_id"],
            ["app.login_challenges.id"],
            name=op.f("fk_access_sessions_challenge_id_login_challenges"),
        ),
        sa.ForeignKeyConstraint(
            ["machine_id"], ["app.machines.id"], name=op.f("fk_access_sessions_machine_id_machines")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app.users.id"], name=op.f("fk_access_sessions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_access_sessions")),
        sa.UniqueConstraint("challenge_id", name=op.f("uq_access_sessions_challenge_id")),
        schema="app",
    )
    op.create_index(
        "ix_access_sessions_machine_started",
        "access_sessions",
        ["machine_id", sa.literal_column("started_at DESC")],
        unique=False,
        schema="app",
    )
    op.create_index(
        "ix_access_sessions_started", "access_sessions", ["started_at"], unique=False, schema="app"
    )
    op.create_index(
        "ix_access_sessions_user_started",
        "access_sessions",
        ["user_id", sa.literal_column("started_at DESC")],
        unique=False,
        schema="app",
    )
    op.create_index(
        "uq_access_sessions_open_machine",
        "access_sessions",
        ["machine_id"],
        unique=True,
        schema="app",
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    op.create_index(
        "uq_access_sessions_open_user",
        "access_sessions",
        ["user_id"],
        unique=True,
        schema="app",
        postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_access_sessions_open_user",
        table_name="access_sessions",
        schema="app",
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    op.drop_index(
        "uq_access_sessions_open_machine",
        table_name="access_sessions",
        schema="app",
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    op.drop_index("ix_access_sessions_user_started", table_name="access_sessions", schema="app")
    op.drop_index("ix_access_sessions_started", table_name="access_sessions", schema="app")
    op.drop_index("ix_access_sessions_machine_started", table_name="access_sessions", schema="app")
    op.drop_table("access_sessions", schema="app")
    op.drop_index(
        op.f("ix_login_challenges_machine_id_created_at"),
        table_name="login_challenges",
        schema="app",
    )
    op.drop_table("login_challenges", schema="app")
    op.drop_table("enrollment_codes", schema="app")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens", schema="app")
    op.drop_index(op.f("ix_refresh_tokens_family_id"), table_name="refresh_tokens", schema="app")
    op.drop_table("refresh_tokens", schema="app")
    op.drop_table("machines", schema="app")
    op.drop_table("users", schema="app")
    op.drop_table("labs", schema="app")
    op.drop_index(op.f("ix_audit_log_created_at"), table_name="audit_log", schema="app")
    op.drop_index(op.f("ix_audit_log_action"), table_name="audit_log", schema="app")
    op.drop_table("audit_log", schema="app")
    for enum_name in (
        "session_end_reason",
        "challenge_status",
        "machine_mode",
        "machine_status",
        "user_status",
        "user_role",
        "audit_actor_type",
    ):
        op.execute(f"DROP TYPE IF EXISTS app.{enum_name}")
