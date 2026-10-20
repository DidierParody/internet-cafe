"""Esquemas de entrada y salida de la API (contrato en snake_case)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------- Autenticación ----------


class RegisterIn(StrictModel):
    email: EmailStr
    student_code: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    privacy_consent: Literal[True]


class LoginIn(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserSummary(BaseModel):
    id: uuid.UUID
    full_name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105 (tipo de token, no un secreto)
    expires_in: int
    user: UserSummary


class ChangePasswordIn(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    student_code_masked: str | None
    role: str
    status: str
    created_at: datetime


class Accepted(BaseModel):
    status: Literal["accepted"] = "accepted"


# ---------- Equipos, salas y sesiones ----------


class MachineRef(BaseModel):
    id: uuid.UUID
    code: str
    lab: str | None


class SessionOut(BaseModel):
    id: uuid.UUID
    status: Literal["active", "ended"]
    started_at: datetime
    ended_at: datetime | None = None
    end_reason: str | None = None
    duration_s: int | None = None
    machine: MachineRef


class SessionPage(BaseModel):
    items: list[SessionOut]
    next_cursor: str | None


class ActiveSessionOut(BaseModel):
    session: SessionOut | None


class ScanIn(StrictModel):
    token: str = Field(min_length=20, max_length=100)


class ActiveSessionRef(BaseModel):
    machine_code: str


class PreviewOut(BaseModel):
    machine: MachineRef
    expires_at: datetime
    active_session: ActiveSessionRef | None


class ClaimOut(BaseModel):
    session: SessionOut


# ---------- Equipo (PC) ----------


class EnrollIn(StrictModel):
    enrollment_code: str = Field(min_length=8, max_length=20)
    hostname: str | None = Field(default=None, max_length=63)
    app_version: str | None = Field(default=None, max_length=20)


class EnrollOut(BaseModel):
    machine_id: uuid.UUID
    code: str
    lab: str | None
    mode: str
    machine_token: str


class ChallengeOut(BaseModel):
    challenge_id: uuid.UUID
    qr_url: str
    expires_at: datetime
    rotate_after_s: int


class RecentAccess(BaseModel):
    machine_code: str
    lab: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_s: int | None


class MachineSessionOut(BaseModel):
    session: dict[str, object]
    user: dict[str, str | None]
    recent_accesses: list[RecentAccess]


class WaitOut(BaseModel):
    status: Literal["waiting", "approved"]
    session: MachineSessionOut | None


class HeartbeatIn(StrictModel):
    session_id: uuid.UUID | None = None
    app_version: str | None = Field(default=None, max_length=20)


class HeartbeatOut(BaseModel):
    server_time: datetime
    mode: str
    session_status: Literal["active", "ended"] | None


class EndSessionIn(StrictModel):
    reason: Literal["user_logout_pc", "machine_shutdown"] = "user_logout_pc"


# ---------- Administración ----------


class LabIn(StrictModel):
    name: str = Field(min_length=2, max_length=80)
    building: str | None = Field(default=None, max_length=80)


class LabOut(BaseModel):
    id: uuid.UUID
    name: str
    building: str | None


class MachineIn(StrictModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    lab_id: uuid.UUID | None = None
    mode: Literal["passive", "kiosk"] = "passive"


class MachinePatch(StrictModel):
    lab_id: uuid.UUID | None = None
    mode: Literal["passive", "kiosk"] | None = None
    status: Literal["active", "disabled"] | None = None


class MachineOut(BaseModel):
    id: uuid.UUID
    code: str
    lab: str | None
    lab_id: uuid.UUID | None
    status: str
    mode: str
    online: bool
    last_seen_at: datetime | None
    app_version: str | None


class EnrollmentCodeOut(BaseModel):
    code: str
    expires_at: datetime


class AdminSessionOut(SessionOut):
    student_name: str
    student_code_masked: str | None
