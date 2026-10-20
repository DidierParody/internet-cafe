"""Escaneo del QR desde el celular: vista previa y confirmación."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.db import get_db
from app.models import User
from app.schemas import ActiveSessionRef, ClaimOut, PreviewOut, ScanIn
from app.services import qr, sessions
from app.services.notifier import MachineNotifier

router = APIRouter(prefix="/scan", tags=["escaneo"])


@router.post("/preview")
async def preview(
    body: ScanIn,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PreviewOut:
    result = await qr.preview(db, user, body.token)
    other = None
    if result.other_session is not None:
        ref = await sessions.machine_ref(db, result.other_session.machine_id)
        other = ActiveSessionRef(machine_code=ref.code)
    return PreviewOut(
        machine=await sessions.machine_ref(db, result.machine.id),
        expires_at=result.challenge.expires_at,
        active_session=other,
    )


@router.post("/claim", status_code=201)
async def claim(
    body: ScanIn,
    request: Request,
    response: Response,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClaimOut:
    session, created = await qr.claim(db, user, body.token)
    if created:
        notifier: MachineNotifier = request.app.state.notifier
        notifier.notify(session.machine_id)
    else:
        response.status_code = 200
    return ClaimOut(session=await sessions.to_out(db, session))
