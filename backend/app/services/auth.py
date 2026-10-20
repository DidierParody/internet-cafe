"""Inicio de sesión, renovación rotativa del refresh token y cierre de sesión web."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ids import uuid7
from app.core.passwords import DUMMY_HASH, hash_password, verify_password
from app.core.tokens import hash_token, issue_access_token, new_opaque_token
from app.models import AuditActorType, RefreshToken, User, UserStatus
from app.services import audit, users

INVALID_CREDENTIALS = AppError(401, "AUTH_INVALID_CREDENTIALS", "Correo o contraseña incorrectos")
REFRESH_INVALID = AppError(401, "AUTH_REFRESH_INVALID", "La sesión web expiró, inicia sesión")


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    user: User


def _now() -> datetime:
    return datetime.now(UTC)


def _new_refresh(
    user_id: uuid.UUID, family_id: uuid.UUID, user_agent: str | None
) -> tuple[RefreshToken, str]:
    plain = new_opaque_token()
    token = RefreshToken(
        id=uuid7(),
        user_id=user_id,
        family_id=family_id,
        token_hash=hash_token(plain),
        expires_at=_now() + timedelta(seconds=get_settings().refresh_token_ttl_s),
        user_agent=(user_agent or "")[:255] or None,
    )
    return token, plain


def _access(user: User) -> str:
    return issue_access_token(subject=str(user.id), role=user.role.value)


def _ensure_can_sign_in(user: User) -> None:
    if user.status == UserStatus.PENDING_VERIFICATION:
        raise AppError(403, "AUTH_EMAIL_NOT_VERIFIED", "Debes verificar tu correo")
    if user.status == UserStatus.BLOCKED:
        raise AppError(403, "FORBIDDEN", "Cuenta bloqueada")


async def login(
    db: AsyncSession, email: str, password: str, user_agent: str | None
) -> IssuedTokens:
    settings = get_settings()
    user = await users.find_by_email(db, email)
    if user is None:
        verify_password(password, DUMMY_HASH)
        raise INVALID_CREDENTIALS
    now = _now()
    if user.locked_until and user.locked_until > now:
        raise AppError(423, "AUTH_ACCOUNT_LOCKED", "Cuenta bloqueada temporalmente")
    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.max_failed_logins:
            user.locked_until = now + timedelta(seconds=settings.lockout_s)
            user.failed_login_count = 0
            audit.record(db, actor_type=AuditActorType.USER, actor_id=user.id, action="auth.locked")
        await db.commit()
        raise INVALID_CREDENTIALS
    _ensure_can_sign_in(user)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    token, plain = _new_refresh(user.id, uuid7(), user_agent)
    db.add(token)
    await db.commit()
    return IssuedTokens(_access(user), plain, user)


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def refresh(db: AsyncSession, plain: str | None, user_agent: str | None) -> IssuedTokens:
    if not plain:
        raise REFRESH_INVALID
    now = _now()
    current = (
        await db.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_token(plain))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if current is None or current.expires_at <= now:
        raise REFRESH_INVALID
    if current.revoked_at is not None:
        within_grace = current.replaced_by is not None and (now - current.revoked_at) <= timedelta(
            seconds=get_settings().refresh_grace_s
        )
        if not within_grace:
            # Reutilización de un token ya rotado: posible robo, se revoca toda la familia.
            await _revoke_family(db, current.family_id)
            audit.record(
                db,
                actor_type=AuditActorType.USER,
                actor_id=current.user_id,
                action="auth.refresh_reuse",
            )
            await db.commit()
            raise REFRESH_INVALID
    user = await db.get(User, current.user_id)
    if user is None:
        raise REFRESH_INVALID
    _ensure_can_sign_in(user)
    token, new_plain = _new_refresh(user.id, current.family_id, user_agent)
    db.add(token)
    await db.flush()
    if current.revoked_at is None:
        current.revoked_at = now
        current.replaced_by = token.id
    await db.commit()
    return IssuedTokens(_access(user), new_plain, user)


async def logout(db: AsyncSession, plain: str | None) -> None:
    if not plain:
        return
    current = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(plain)))
    ).scalar_one_or_none()
    if current is not None:
        await _revoke_family(db, current.family_id)
        await db.commit()


async def change_password(db: AsyncSession, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise INVALID_CREDENTIALS
    user.password_hash = hash_password(new)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    audit.record(
        db, actor_type=AuditActorType.USER, actor_id=user.id, action="auth.password_changed"
    )
    await db.commit()
