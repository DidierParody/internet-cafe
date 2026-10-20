"""Usuarios: creación con datos personales cifrados y lectura descifrada."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.ids import uuid7
from app.core.passwords import hash_password
from app.models import User, UserRole, UserStatus

AAD_EMAIL = "users.email"
AAD_CODE = "users.student_code"
AAD_NAME = "users.full_name"


@dataclass(frozen=True)
class UserView:
    id: uuid.UUID
    email: str
    full_name: str
    student_code: str | None
    role: str
    status: str
    created_at: datetime

    @property
    def student_code_masked(self) -> str | None:
        return crypto.mask_code(self.student_code) if self.student_code else None


def view(user: User) -> UserView:
    return UserView(
        id=user.id,
        email=crypto.decrypt(user.email_ct, aad=AAD_EMAIL),
        full_name=crypto.decrypt(user.full_name_ct, aad=AAD_NAME),
        student_code=(
            crypto.decrypt(user.student_code_ct, aad=AAD_CODE) if user.student_code_ct else None
        ),
        role=user.role.value,
        status=user.status.value,
        created_at=user.created_at,
    )


def full_name(user: User) -> str:
    return crypto.decrypt(user.full_name_ct, aad=AAD_NAME)


def masked_code(user: User) -> str | None:
    if not user.student_code_ct:
        return None
    return crypto.mask_code(crypto.decrypt(user.student_code_ct, aad=AAD_CODE))


async def find_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email_bidx == crypto.blind_index(email)))
    return result.scalar_one_or_none()


async def exists(db: AsyncSession, email: str, student_code: str | None) -> bool:
    conditions = [User.email_bidx == crypto.blind_index(email)]
    if student_code:
        conditions.append(User.student_code_bidx == crypto.blind_index(student_code))
    result = await db.execute(select(User.id).where(or_(*conditions)).limit(1))
    return result.first() is not None


def new_user(
    *,
    email: str,
    full_name: str,
    password: str,
    student_code: str | None,
    role: UserRole = UserRole.STUDENT,
    active: bool,
) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid7(),
        email_ct=crypto.encrypt(crypto.normalize(email), aad=AAD_EMAIL),
        email_bidx=crypto.blind_index(email),
        student_code_ct=crypto.encrypt(student_code, aad=AAD_CODE) if student_code else None,
        student_code_bidx=crypto.blind_index(student_code) if student_code else None,
        full_name_ct=crypto.encrypt(full_name, aad=AAD_NAME),
        password_hash=hash_password(password),
        role=role,
        status=UserStatus.ACTIVE if active else UserStatus.PENDING_VERIFICATION,
        privacy_consent_at=now,
    )
