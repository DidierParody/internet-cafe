"""Panel de administración mínimo: salas, equipos, códigos de enrolamiento y accesos."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.models import (
    AccessSession,
    AuditActorType,
    Lab,
    Machine,
    MachineMode,
    MachineStatus,
    SessionEndReason,
    User,
)
from app.schemas import (
    AdminSessionOut,
    EnrollmentCodeOut,
    LabIn,
    LabOut,
    MachineIn,
    MachineOut,
    MachinePatch,
)
from app.services import audit, qr, sessions, users

router = APIRouter(prefix="/admin", tags=["administración"])

CONFLICT = AppError(409, "CONFLICT", "Ya existe un registro con ese nombre o código")
MACHINE_NOT_FOUND = AppError(404, "NOT_FOUND", "Equipo no encontrado")


@router.get("/labs")
async def list_labs(
    _: Annotated[User, Depends(require_admin)], db: Annotated[AsyncSession, Depends(get_db)]
) -> list[LabOut]:
    labs = (await db.execute(select(Lab).order_by(Lab.name))).scalars()
    return [LabOut(id=x.id, name=x.name, building=x.building) for x in labs]


@router.post("/labs", status_code=201)
async def create_lab(
    body: LabIn,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LabOut:
    lab = Lab(name=body.name, building=body.building)
    db.add(lab)
    audit.record(db, actor_type=AuditActorType.USER, actor_id=admin.id, action="lab.created")
    try:
        await db.commit()
    except IntegrityError as exc:
        raise CONFLICT from exc
    return LabOut(id=lab.id, name=lab.name, building=lab.building)


def _machine_out(machine: Machine, lab_name: str | None) -> MachineOut:
    online_after = datetime.now(UTC) - timedelta(seconds=get_settings().machine_online_s)
    return MachineOut(
        id=machine.id,
        code=machine.code,
        lab=lab_name,
        lab_id=machine.lab_id,
        status=machine.status.value,
        mode=machine.mode.value,
        online=bool(machine.last_seen_at and machine.last_seen_at >= online_after),
        last_seen_at=machine.last_seen_at,
        app_version=machine.app_version,
    )


async def _lab_name(db: AsyncSession, lab_id: uuid.UUID | None) -> str | None:
    if lab_id is None:
        return None
    lab = await db.get(Lab, lab_id)
    if lab is None:
        raise AppError(422, "VALIDATION_ERROR", "La sala no existe")
    return lab.name


@router.get("/machines")
async def list_machines(
    _: Annotated[User, Depends(require_admin)], db: Annotated[AsyncSession, Depends(get_db)]
) -> list[MachineOut]:
    rows = await db.execute(
        select(Machine, Lab.name)
        .join(Lab, Lab.id == Machine.lab_id, isouter=True)
        .order_by(Machine.code)
    )
    return [_machine_out(m, lab) for m, lab in rows.all()]


@router.post("/machines", status_code=201)
async def create_machine(
    body: MachineIn,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MachineOut:
    lab_name = await _lab_name(db, body.lab_id)
    machine = Machine(code=body.code.upper(), lab_id=body.lab_id, mode=MachineMode(body.mode))
    db.add(machine)
    audit.record(db, actor_type=AuditActorType.USER, actor_id=admin.id, action="machine.created")
    try:
        await db.commit()
    except IntegrityError as exc:
        raise CONFLICT from exc
    return _machine_out(machine, lab_name)


async def _machine(db: AsyncSession, machine_id: uuid.UUID) -> Machine:
    machine = await db.get(Machine, machine_id)
    if machine is None:
        raise MACHINE_NOT_FOUND
    return machine


@router.patch("/machines/{machine_id}")
async def update_machine(
    machine_id: uuid.UUID,
    body: MachinePatch,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MachineOut:
    machine = await _machine(db, machine_id)
    if "lab_id" in body.model_fields_set:
        await _lab_name(db, body.lab_id)
        machine.lab_id = body.lab_id
    if body.mode is not None:
        machine.mode = MachineMode(body.mode)
    if body.status is not None:
        if body.status == "active" and machine.api_token_hash is None:
            raise AppError(409, "CONFLICT", "El equipo aún no está enrolado")
        machine.status = MachineStatus(body.status)
    audit.record(
        db,
        actor_type=AuditActorType.USER,
        actor_id=admin.id,
        action="machine.updated",
        target_type="machine",
        target_id=machine.id,
    )
    await db.commit()
    return _machine_out(machine, await _lab_name(db, machine.lab_id))


@router.post("/machines/{machine_id}/enrollment-codes", status_code=201)
async def create_enrollment_code(
    machine_id: uuid.UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnrollmentCodeOut:
    machine = await _machine(db, machine_id)
    record, plain = await qr.create_enrollment_code(db, machine, admin)
    return EnrollmentCodeOut(code=plain, expires_at=record.expires_at)


async def _admin_session_out(db: AsyncSession, session: AccessSession) -> AdminSessionOut:
    base = await sessions.to_out(db, session)
    student = await db.get(User, session.user_id)
    if student is None:
        raise sessions.SESSION_NOT_FOUND
    return AdminSessionOut(
        **base.model_dump(),
        student_name=users.full_name(student),
        student_code_masked=users.masked_code(student),
    )


@router.get("/sessions")
async def list_sessions(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    active: bool | None = None,
    machine_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    criteria: list[ColumnElement[bool]] = []
    if active is True:
        criteria.append(AccessSession.ended_at.is_(None))
    elif active is False:
        criteria.append(AccessSession.ended_at.is_not(None))
    if machine_id is not None:
        criteria.append(AccessSession.machine_id == machine_id)
    rows, next_cursor = await sessions.page(db, *criteria, limit=limit, cursor=cursor)
    return {
        "items": [(await _admin_session_out(db, s)).model_dump(mode="json") for s in rows],
        "next_cursor": next_cursor,
    }


@router.post("/sessions/{session_id}/end")
async def force_end_session(
    session_id: uuid.UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminSessionOut:
    session = await db.get(AccessSession, session_id)
    if session is None:
        raise sessions.SESSION_NOT_FOUND
    sessions.end(session, SessionEndReason.ADMIN_FORCED)
    audit.record(
        db,
        actor_type=AuditActorType.USER,
        actor_id=admin.id,
        action="session.force_ended",
        target_type="access_session",
        target_id=session.id,
    )
    await db.commit()
    return await _admin_session_out(db, session)
