"""Dependencias de autenticación y autorización."""

import uuid
from datetime import UTC, datetime

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.core.tokens import InvalidTokenError, decode_access_token, hash_token
from app.models import Machine, MachineStatus, User, UserRole, UserStatus

_bearer = HTTPBearer(auto_error=False)

UNAUTHENTICATED = AppError(
    401, "UNAUTHORIZED", "No autenticado", headers={"WWW-Authenticate": "Bearer"}
)


async def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UNAUTHENTICATED
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(claims["sub"]))
    except (InvalidTokenError, KeyError, ValueError) as exc:
        raise AppError(401, "AUTH_TOKEN_EXPIRED", "Sesión expirada o token inválido") from exc
    user = await db.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise UNAUTHENTICATED
    return user


async def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise AppError(403, "FORBIDDEN", "Requiere rol de administrador")
    return user


async def current_machine(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Machine:
    """PoC: el equipo se autentica con su token Bearer (en el MVP, firma RFC 9421)."""
    if credentials is None:
        raise UNAUTHENTICATED
    machine = (
        await db.execute(
            select(Machine).where(Machine.api_token_hash == hash_token(credentials.credentials))
        )
    ).scalar_one_or_none()
    if machine is None:
        raise AppError(401, "MACHINE_TOKEN_INVALID", "Equipo no autenticado")
    if machine.status != MachineStatus.ACTIVE:
        raise AppError(403, "MACHINE_DISABLED", "Equipo deshabilitado")
    machine.last_seen_at = datetime.now(UTC)
    return machine


def check_origin(request: Request) -> None:
    """Endpoints con cookie: si el navegador envía Origin, debe ser el del frontend."""
    origin = request.headers.get("origin")
    if origin and origin not in get_settings().allowed_origins:
        raise AppError(403, "FORBIDDEN", "Origen no permitido")
