"""Endpoints del equipo (PC). PoC: autenticación con token Bearer, sin firma."""

import asyncio
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_machine
from app.core.config import get_settings
from app.core.db import get_db
from app.models import AccessSession, Machine, SessionEndReason
from app.schemas import (
    ChallengeOut,
    EndSessionIn,
    EnrollIn,
    EnrollOut,
    HeartbeatIn,
    HeartbeatOut,
    MachineSessionOut,
    SessionOut,
    WaitOut,
)
from app.services import qr, sessions
from app.services.notifier import MachineNotifier

router = APIRouter(prefix="/machine", tags=["equipo"])


def _notifier(request: Request) -> MachineNotifier:
    notifier: MachineNotifier = request.app.state.notifier
    return notifier


@router.post("/enroll", status_code=201)
async def enroll(body: EnrollIn, db: Annotated[AsyncSession, Depends(get_db)]) -> EnrollOut:
    machine, token = await qr.enroll(db, body.enrollment_code, body.hostname, body.app_version)
    ref = await sessions.machine_ref(db, machine.id)
    return EnrollOut(
        machine_id=machine.id,
        code=machine.code,
        lab=ref.lab,
        mode=machine.mode.value,
        machine_token=token,
    )


@router.post("/challenges", status_code=201)
async def create_challenge(
    machine: Annotated[Machine, Depends(current_machine)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChallengeOut:
    settings = get_settings()
    challenge, token = await qr.create_challenge(db, machine)
    return ChallengeOut(
        challenge_id=challenge.id,
        qr_url=f"{settings.frontend_base_url.rstrip('/')}/s#{token}",
        expires_at=challenge.expires_at,
        rotate_after_s=settings.challenge_rotate_s,
    )


@router.get("/challenges/wait")
async def wait_for_login(
    request: Request,
    machine: Annotated[Machine, Depends(current_machine)],
    db: Annotated[AsyncSession, Depends(get_db)],
    timeout: Annotated[int, Query(ge=0, le=60)] = 25,  # noqa: ASYNC109 (parámetro HTTP)
) -> WaitOut:
    """Long-poll por equipo: responde en cuanto un estudiante confirma, o al vencer."""
    event = _notifier(request).subscribe(machine.id)  # suscribirse ANTES de leer
    await db.commit()  # guarda last_seen_at y libera la conexión
    view = await _load_view(db, machine)
    if view is not None:
        return WaitOut(status="approved", session=view)
    try:
        await asyncio.wait_for(event.wait(), timeout=min(timeout, get_settings().long_poll_max_s))
    except TimeoutError:
        return WaitOut(status="waiting", session=None)
    view = await _load_view(db, machine)
    return WaitOut(status="approved" if view else "waiting", session=view)


async def _load_view(db: AsyncSession, machine: Machine) -> MachineSessionOut | None:
    session = await sessions.open_for_machine(db, machine.id)
    view: dict[str, Any] | None = (
        await sessions.machine_view(db, session) if session is not None else None
    )
    await db.commit()  # no retener la conexión mientras el equipo espera
    return MachineSessionOut.model_validate(view) if view else None


@router.get("/sessions/current", response_model=MachineSessionOut)
async def current_session(
    machine: Annotated[Machine, Depends(current_machine)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    view = await _load_view(db, machine)
    if view is None:
        return Response(status_code=204)
    return view


@router.post("/sessions/current/end")
async def end_current_session(
    machine: Annotated[Machine, Depends(current_machine)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: EndSessionIn | None = None,
) -> SessionOut | None:
    session = await sessions.open_for_machine(db, machine.id)
    if session is None:
        await db.commit()
        return None
    reason = SessionEndReason((body or EndSessionIn()).reason)
    sessions.end(session, reason)
    await db.commit()
    return await sessions.to_out(db, session)


@router.post("/heartbeat")
async def heartbeat(
    body: HeartbeatIn,
    machine: Annotated[Machine, Depends(current_machine)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HeartbeatOut:
    if body.app_version:
        machine.app_version = body.app_version
    current = await sessions.open_for_machine(db, machine.id)
    if current is not None:
        current.last_heartbeat_at = datetime.now(UTC)
    status: str | None = "active" if current is not None else None
    if body.session_id is not None and (current is None or current.id != body.session_id):
        reported = await db.get(AccessSession, body.session_id)
        if reported is not None and reported.machine_id == machine.id:
            status = "ended"
    await db.commit()
    return HeartbeatOut(
        server_time=datetime.now(UTC),
        mode=machine.mode.value,
        session_status=status,
    )
