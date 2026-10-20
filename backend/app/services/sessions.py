"""Sesiones de acceso: consulta, cierre, vistas para el equipo y el estudiante."""

import base64
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import AccessSession, Lab, Machine, SessionEndReason, User
from app.schemas import MachineRef, RecentAccess, SessionOut
from app.services import users

SESSION_NOT_FOUND = AppError(404, "SESSION_NOT_FOUND", "Sesión no encontrada")


def now() -> datetime:
    return datetime.now(UTC)


def _timeout() -> timedelta:
    return timedelta(seconds=get_settings().session_timeout_s)


def is_stale(session: AccessSession, at: datetime | None = None) -> bool:
    return session.ended_at is None and session.last_heartbeat_at < (at or now()) - _timeout()


def end(session: AccessSession, reason: SessionEndReason, at: datetime | None = None) -> None:
    if session.ended_at is not None:
        return
    if reason == SessionEndReason.HEARTBEAT_TIMEOUT:
        session.ended_at = session.last_heartbeat_at
    else:
        session.ended_at = max(at or now(), session.started_at)
    session.end_reason = reason


async def _open_where(db: AsyncSession, *criteria: Any) -> AccessSession | None:
    session = (
        await db.execute(select(AccessSession).where(AccessSession.ended_at.is_(None), *criteria))
    ).scalar_one_or_none()
    if session is not None and is_stale(session):
        # Cierre perezoso: si el latido venció, se cierra con la hora del último latido.
        end(session, SessionEndReason.HEARTBEAT_TIMEOUT)
        await db.flush()
        return None
    return session


async def open_for_machine(db: AsyncSession, machine_id: uuid.UUID) -> AccessSession | None:
    return await _open_where(db, AccessSession.machine_id == machine_id)


async def open_for_user(db: AsyncSession, user_id: uuid.UUID) -> AccessSession | None:
    return await _open_where(db, AccessSession.user_id == user_id)


async def machine_ref(db: AsyncSession, machine_id: uuid.UUID) -> MachineRef:
    row = (
        await db.execute(
            select(Machine.id, Machine.code, Lab.name)
            .join(Lab, Lab.id == Machine.lab_id, isouter=True)
            .where(Machine.id == machine_id)
        )
    ).one()
    return MachineRef(id=row[0], code=row[1], lab=row[2])


def _duration(session: AccessSession) -> int | None:
    if session.ended_at is None:
        return None
    return int((session.ended_at - session.started_at).total_seconds())


async def to_out(db: AsyncSession, session: AccessSession) -> SessionOut:
    return SessionOut(
        id=session.id,
        status="active" if session.ended_at is None else "ended",
        started_at=session.started_at,
        ended_at=session.ended_at,
        end_reason=session.end_reason.value if session.end_reason else None,
        duration_s=_duration(session),
        machine=await machine_ref(db, session.machine_id),
    )


async def recent_accesses(
    db: AsyncSession, user_id: uuid.UUID, exclude: uuid.UUID | None, limit: int = 5
) -> list[RecentAccess]:
    query = (
        select(AccessSession, Machine.code, Lab.name)
        .join(Machine, Machine.id == AccessSession.machine_id)
        .join(Lab, Lab.id == Machine.lab_id, isouter=True)
        .where(AccessSession.user_id == user_id, AccessSession.ended_at.is_not(None))
        .order_by(AccessSession.started_at.desc())
        .limit(limit)
    )
    if exclude is not None:
        query = query.where(AccessSession.id != exclude)
    rows = (await db.execute(query)).all()
    return [
        RecentAccess(
            machine_code=code,
            lab=lab,
            started_at=s.started_at,
            ended_at=s.ended_at,
            duration_s=_duration(s),
        )
        for s, code, lab in rows
    ]


async def machine_view(db: AsyncSession, session: AccessSession) -> dict[str, Any]:
    """Lo que muestra el tablero del PC: datos mínimos del estudiante (sin correo)."""
    user = await db.get(User, session.user_id)
    if user is None:
        raise SESSION_NOT_FOUND
    return {
        "session": {"id": str(session.id), "started_at": session.started_at.isoformat()},
        "user": {
            "full_name": users.full_name(user),
            "student_code_masked": users.masked_code(user),
        },
        "recent_accesses": [
            r.model_dump(mode="json")
            for r in await recent_accesses(db, session.user_id, exclude=session.id)
        ],
    }


def encode_cursor(session: AccessSession) -> str:
    raw = f"{session.started_at.isoformat()}|{session.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        started, sid = base64.urlsafe_b64decode(cursor.encode()).decode().split("|", 1)
        return datetime.fromisoformat(started), uuid.UUID(sid)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError(422, "VALIDATION_ERROR", "Cursor inválido") from exc


async def page(
    db: AsyncSession, *criteria: Any, limit: int, cursor: str | None
) -> tuple[list[AccessSession], str | None]:
    query = select(AccessSession).where(*criteria)
    if cursor:
        started, sid = decode_cursor(cursor)
        query = query.where(tuple_(AccessSession.started_at, AccessSession.id) < (started, sid))
    rows = list(
        (
            await db.execute(
                query.order_by(AccessSession.started_at.desc(), AccessSession.id.desc()).limit(
                    limit + 1
                )
            )
        ).scalars()
    )
    next_cursor = encode_cursor(rows[limit - 1]) if len(rows) > limit else None
    return rows[:limit], next_cursor
