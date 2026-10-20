from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_origin
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.models import AuditActorType
from app.schemas import Accepted, LoginIn, RegisterIn, TokenOut, UserSummary
from app.services import audit, users
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["autenticación"])

REFRESH_COOKIE = "__Secure-rt"
COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, value: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        value,
        max_age=settings.refresh_token_ttl_s,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _token_out(issued: auth_service.IssuedTokens) -> TokenOut:
    return TokenOut(
        access_token=issued.access_token,
        expires_in=get_settings().access_token_ttl_s,
        user=UserSummary(
            id=issued.user.id, full_name=users.full_name(issued.user), role=issued.user.role.value
        ),
    )


@router.post("/register", status_code=202)
async def register(body: RegisterIn, db: Annotated[AsyncSession, Depends(get_db)]) -> Accepted:
    settings = get_settings()
    domain = body.email.rsplit("@", 1)[1].lower()
    if settings.email_domains and domain not in settings.email_domains:
        raise AppError(422, "VALIDATION_ERROR", "Usa tu correo institucional")
    # Respuesta genérica: no se revela si el correo o el código ya existen.
    if await users.exists(db, body.email, body.student_code):
        audit.record(
            db, actor_type=AuditActorType.SYSTEM, actor_id=None, action="auth.register_conflict"
        )
        await db.commit()
        return Accepted()
    user = users.new_user(
        email=body.email,
        full_name=body.full_name,
        password=body.password,
        student_code=body.student_code,
        active=not settings.require_email_verification,
    )
    db.add(user)
    await db.commit()
    return Accepted()


@router.post("/login")
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenOut:
    issued = await auth_service.login(
        db, body.email, body.password, request.headers.get("user-agent")
    )
    _set_refresh_cookie(response, issued.refresh_token)
    return _token_out(issued)


@router.post("/refresh", dependencies=[Depends(check_origin)])
async def refresh(
    request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenOut:
    issued = await auth_service.refresh(
        db, request.cookies.get(REFRESH_COOKIE), request.headers.get("user-agent")
    )
    _set_refresh_cookie(response, issued.refresh_token)
    return _token_out(issued)


@router.post("/logout", status_code=204, dependencies=[Depends(check_origin)])
async def logout(
    request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    await auth_service.logout(db, request.cookies.get(REFRESH_COOKIE))
    response.delete_cookie(
        REFRESH_COOKIE,
        path=COOKIE_PATH,
        secure=get_settings().cookie_secure,
        httponly=True,
        samesite="strict",
    )
