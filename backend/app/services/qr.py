"""Enrolamiento de equipos, retos QR, vista previa y confirmación (secciones 8.1 y 8.2)."""

import re
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ids import uuid7
from app.core.tokens import hash_token, new_opaque_token
from app.models import (
    AccessSession,
    AuditActorType,
    ChallengeStatus,
    EnrollmentCode,
    LoginChallenge,
    Machine,
    MachineStatus,
    SessionEndReason,
    User,
)
from app.services import audit, sessions
from app.services.sessions import now

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I

NOT_FOUND = AppError(404, "CHALLENGE_NOT_FOUND", "Código QR no válido", "Escanea el QR del equipo.")
EXPIRED = AppError(
    410, "CHALLENGE_EXPIRED", "El código QR expiró", "Escanea el código nuevo del equipo."
)
USED = AppError(409, "CHALLENGE_ALREADY_USED", "El código QR ya se usó", "Escanea el código nuevo.")
BUSY = AppError(409, "MACHINE_BUSY", "El equipo ya tiene una sesión activa")
DISABLED = AppError(403, "MACHINE_DISABLED", "Equipo deshabilitado")
ENROLL_INVALID = AppError(
    401, "ENROLLMENT_CODE_INVALID", "Código de enrolamiento inválido o vencido"
)


# ---------- Enrolamiento ----------


def _normalize_code(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", code.upper())


async def create_enrollment_code(
    db: AsyncSession, machine: Machine, admin: User
) -> tuple[EnrollmentCode, str]:
    """Devuelve el registro y el código en claro (se muestra una sola vez)."""
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    code = EnrollmentCode(
        machine_id=machine.id,
        code_hash=hash_token(raw),
        created_by=admin.id,
        expires_at=now() + timedelta(seconds=get_settings().enrollment_code_ttl_s),
    )
    db.add(code)
    audit.record(
        db,
        actor_type=AuditActorType.USER,
        actor_id=admin.id,
        action="machine.enrollment_code_created",
        target_type="machine",
        target_id=machine.id,
    )
    await db.commit()
    return code, f"{raw[:4]}-{raw[4:]}"


async def enroll(
    db: AsyncSession, code: str, hostname: str | None, app_version: str | None
) -> tuple[Machine, str]:
    record = (
        await db.execute(
            select(EnrollmentCode)
            .where(EnrollmentCode.code_hash == hash_token(_normalize_code(code)))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if record is None or record.used_at is not None or record.expires_at <= now():
        raise ENROLL_INVALID
    machine = await db.get(Machine, record.machine_id)
    if machine is None or machine.status == MachineStatus.DISABLED:
        raise ENROLL_INVALID
    token = "mt_" + new_opaque_token()
    record.used_at = now()
    machine.api_token_hash = hash_token(token)
    machine.status = MachineStatus.ACTIVE
    machine.enrolled_at = now()
    machine.hostname = hostname
    machine.app_version = app_version
    audit.record(
        db,
        actor_type=AuditActorType.MACHINE,
        actor_id=machine.id,
        action="machine.enrolled",
        target_type="machine",
        target_id=machine.id,
    )
    await db.commit()
    return machine, token


# ---------- Retos QR ----------


async def create_challenge(db: AsyncSession, machine: Machine) -> tuple[LoginChallenge, str]:
    settings = get_settings()
    # Si el equipo pide un QR, no hay nadie usándolo: se cierra cualquier sesión huérfana.
    orphan = await sessions.open_for_machine(db, machine.id)
    if orphan is not None:
        sessions.end(orphan, SessionEndReason.SUPERSEDED)
    # Como máximo 2 QR vigentes: se conserva solo el pendiente más reciente.
    newest_pending = (
        await db.execute(
            select(LoginChallenge.id)
            .where(
                LoginChallenge.machine_id == machine.id,
                LoginChallenge.status == ChallengeStatus.PENDING,
            )
            .order_by(LoginChallenge.created_at.desc(), LoginChallenge.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    cancel = update(LoginChallenge).where(
        LoginChallenge.machine_id == machine.id, LoginChallenge.status == ChallengeStatus.PENDING
    )
    if newest_pending is not None:
        cancel = cancel.where(LoginChallenge.id != newest_pending)
    await db.execute(cancel.values(status=ChallengeStatus.CANCELLED))
    token = new_opaque_token()
    challenge = LoginChallenge(
        id=uuid7(),
        machine_id=machine.id,
        token_hash=hash_token(token),
        expires_at=now() + timedelta(seconds=settings.challenge_ttl_s),
    )
    db.add(challenge)
    await db.commit()
    return challenge, token


async def _challenge(db: AsyncSession, token: str, *, for_update: bool = False) -> LoginChallenge:
    query = select(LoginChallenge).where(LoginChallenge.token_hash == hash_token(token))
    if for_update:
        query = query.with_for_update()
    challenge = (await db.execute(query)).scalar_one_or_none()
    if challenge is None:
        raise NOT_FOUND
    return challenge


def _ensure_usable(challenge: LoginChallenge) -> None:
    if challenge.status == ChallengeStatus.APPROVED:
        raise USED
    if challenge.status != ChallengeStatus.PENDING or challenge.expires_at <= now():
        raise EXPIRED


async def _active_machine(db: AsyncSession, challenge: LoginChallenge) -> Machine:
    machine = await db.get(Machine, challenge.machine_id)
    if machine is None or machine.status != MachineStatus.ACTIVE:
        raise DISABLED
    return machine


@dataclass(frozen=True)
class Preview:
    challenge: LoginChallenge
    machine: Machine
    other_session: AccessSession | None


async def preview(db: AsyncSession, user: User, token: str) -> Preview:
    challenge = await _challenge(db, token)
    _ensure_usable(challenge)
    machine = await _active_machine(db, challenge)
    other = await sessions.open_for_user(db, user.id)
    if other is not None and other.machine_id == machine.id:
        other = None
    await db.commit()
    return Preview(challenge, machine, other)


async def claim(db: AsyncSession, user: User, token: str) -> tuple[AccessSession, bool]:
    """Crea la sesión de acceso. Devuelve (sesión, creada); idempotente para el mismo usuario."""
    challenge = await _challenge(db, token, for_update=True)
    if challenge.status == ChallengeStatus.APPROVED and challenge.approved_by == user.id:
        existing = (
            await db.execute(
                select(AccessSession).where(AccessSession.challenge_id == challenge.id)
            )
        ).scalar_one()
        return existing, False
    _ensure_usable(challenge)
    machine = await _active_machine(db, challenge)
    at = now()
    previous = await sessions.open_for_user(db, user.id)
    if previous is not None:
        sessions.end(previous, SessionEndReason.SUPERSEDED, at)
    if await sessions.open_for_machine(db, machine.id) is not None:
        raise BUSY
    challenge.status = ChallengeStatus.APPROVED
    challenge.approved_by = user.id
    challenge.approved_at = at
    await db.execute(
        update(LoginChallenge)
        .where(
            LoginChallenge.machine_id == machine.id,
            LoginChallenge.status == ChallengeStatus.PENDING,
            LoginChallenge.id != challenge.id,
        )
        .values(status=ChallengeStatus.CANCELLED)
    )
    session = AccessSession(
        id=uuid7(),
        user_id=user.id,
        machine_id=machine.id,
        challenge_id=challenge.id,
        started_at=at,
        last_heartbeat_at=at,
    )
    db.add(session)
    audit.record(
        db,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="session.started",
        target_type="access_session",
        target_id=session.id,
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BUSY from exc
    return session, True
