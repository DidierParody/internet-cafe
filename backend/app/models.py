"""Modelo de datos (sección 11 del SRS). Todas las tablas viven en el esquema `app`."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    LargeBinary,
    MetaData,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.ids import uuid7

SCHEMA = "app"

NAMING = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA, naming_convention=NAMING)


class UserRole(enum.StrEnum):
    STUDENT = "student"
    ADMIN = "admin"


class UserStatus(enum.StrEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    BLOCKED = "blocked"


class MachineStatus(enum.StrEnum):
    PENDING_ENROLLMENT = "pending_enrollment"
    ACTIVE = "active"
    DISABLED = "disabled"


class MachineMode(enum.StrEnum):
    PASSIVE = "passive"
    KIOSK = "kiosk"


class ChallengeStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SessionEndReason(enum.StrEnum):
    USER_LOGOUT_PC = "user_logout_pc"
    USER_LOGOUT_WEB = "user_logout_web"
    SUPERSEDED = "superseded"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    ADMIN_FORCED = "admin_forced"
    MACHINE_SHUTDOWN = "machine_shutdown"


class AuditActorType(enum.StrEnum):
    USER = "user"
    MACHINE = "machine"
    SYSTEM = "system"


def _enum(cls: type[enum.StrEnum], name: str) -> Enum:
    return Enum(cls, name=name, schema=SCHEMA, values_callable=lambda e: [m.value for m in e])


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _pk()
    email_ct: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    email_bidx: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    student_code_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    student_code_bidx: Mapped[bytes | None] = mapped_column(LargeBinary, unique=True)
    full_name_ct: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        _enum(UserRole, "user_role"), nullable=False, default=UserRole.STUDENT
    )
    status: Mapped[UserStatus] = mapped_column(
        _enum(UserStatus, "user_status"), nullable=False, default=UserStatus.PENDING_VERIFICATION
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    privacy_consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failed_login_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("refresh_tokens.id"))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = _created()


class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    building: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = _created()


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = _pk()
    lab_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("labs.id"))
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    hostname: Mapped[str | None] = mapped_column(String(63))
    status: Mapped[MachineStatus] = mapped_column(
        _enum(MachineStatus, "machine_status"),
        nullable=False,
        default=MachineStatus.PENDING_ENROLLMENT,
    )
    mode: Mapped[MachineMode] = mapped_column(
        _enum(MachineMode, "machine_mode"), nullable=False, default=MachineMode.PASSIVE
    )
    # PoC: token Bearer del equipo. En el MVP se reemplaza por la firma RFC 9421.
    api_token_hash: Mapped[bytes | None] = mapped_column(LargeBinary, unique=True)
    public_key_jwk: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    key_thumbprint: Mapped[str | None] = mapped_column(String(64), unique=True)
    app_version: Mapped[str | None] = mapped_column(String(20))
    enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EnrollmentCode(Base):
    __tablename__ = "enrollment_codes"

    id: Mapped[uuid.UUID] = _pk()
    machine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("machines.id"), nullable=False)
    code_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()


class LoginChallenge(Base):
    __tablename__ = "login_challenges"
    __table_args__ = (Index(None, "machine_id", "created_at"),)

    id: Mapped[uuid.UUID] = _pk()
    machine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("machines.id"), nullable=False)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    status: Mapped[ChallengeStatus] = mapped_column(
        _enum(ChallengeStatus, "challenge_status"), nullable=False, default=ChallengeStatus.PENDING
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _created()


class AccessSession(Base):
    __tablename__ = "access_sessions"
    __table_args__ = (
        CheckConstraint("(ended_at IS NULL) = (end_reason IS NULL)", name="end_consistent"),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="end_after_start"),
        Index(
            "uq_access_sessions_open_machine",
            "machine_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index(
            "uq_access_sessions_open_user",
            "user_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index("ix_access_sessions_user_started", "user_id", text("started_at DESC")),
        Index("ix_access_sessions_machine_started", "machine_id", text("started_at DESC")),
        Index("ix_access_sessions_started", "started_at"),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    machine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("machines.id"), nullable=False)
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("login_challenges.id"), nullable=False, unique=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[SessionEndReason | None] = mapped_column(
        _enum(SessionEndReason, "session_end_reason")
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index(None, "created_at"), Index(None, "action"))

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    actor_type: Mapped[AuditActorType] = mapped_column(
        _enum(AuditActorType, "audit_actor_type"), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(40))
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = _created()
