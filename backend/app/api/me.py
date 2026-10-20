import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.db import get_db
from app.models import AccessSession, SessionEndReason, User
from app.schemas import ActiveSessionOut, ChangePasswordIn, MeOut, SessionOut, SessionPage
from app.services import auth as auth_service
from app.services import sessions, users

router = APIRouter(prefix="/me", tags=["estudiante"])


@router.get("")
async def me(user: Annotated[User, Depends(current_user)]) -> MeOut:
    v = users.view(user)
    return MeOut(
        id=v.id,
        email=v.email,
        full_name=v.full_name,
        student_code_masked=v.student_code_masked,
        role=v.role,
        status=v.status,
        created_at=v.created_at,
    )


@router.patch("/password", status_code=204)
async def change_password(
    body: ChangePasswordIn,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await auth_service.change_password(db, user, body.current_password, body.new_password)


@router.get("/sessions")
async def my_sessions(
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: str | None = None,
) -> SessionPage:
    # Cierra de forma perezosa una sesión vencida antes de listar.
    await sessions.open_for_user(db, user.id)
    await db.commit()
    rows, next_cursor = await sessions.page(
        db, AccessSession.user_id == user.id, limit=limit, cursor=cursor
    )
    return SessionPage(items=[await sessions.to_out(db, s) for s in rows], next_cursor=next_cursor)


@router.get("/sessions/active")
async def my_active_session(
    user: Annotated[User, Depends(current_user)], db: Annotated[AsyncSession, Depends(get_db)]
) -> ActiveSessionOut:
    session = await sessions.open_for_user(db, user.id)
    await db.commit()
    return ActiveSessionOut(session=await sessions.to_out(db, session) if session else None)


@router.post("/sessions/{session_id}/end")
async def end_my_session(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionOut:
    session = await db.get(AccessSession, session_id)
    if session is None or session.user_id != user.id:
        raise sessions.SESSION_NOT_FOUND
    sessions.end(session, SessionEndReason.USER_LOGOUT_WEB)
    await db.commit()
    return await sessions.to_out(db, session)
