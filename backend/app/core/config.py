"""Configuración de la API, leída de variables de entorno (o de backend/.env en local)."""

import base64
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Base de datos: el runtime usa el rol de la app; las migraciones usan el owner.
    database_url: str
    database_url_migrations: str | None = None
    # Solo para `db_admin bootstrap-role`: contraseña del rol svc_app.
    app_db_password: str | None = None

    # Llaves (base64). DATA_ENC_KEY y BLIND_INDEX_KEY deben ser de 32 bytes.
    data_enc_key: str
    blind_index_key: str
    jwt_private_key_b64: str

    frontend_base_url: str = "http://localhost:5173"
    extra_allowed_origins: str = ""
    allowed_email_domains: str = ""
    # PoC: sin proveedor de correo, las cuentas quedan activas al registrarse.
    require_email_verification: bool = False

    access_token_ttl_s: int = 600
    refresh_token_ttl_s: int = 7 * 24 * 3600
    refresh_grace_s: int = 10
    cookie_secure: bool = True

    challenge_ttl_s: int = 60
    challenge_rotate_s: int = 45
    long_poll_max_s: int = 25
    heartbeat_interval_s: int = 60
    session_timeout_s: int = 180
    enrollment_code_ttl_s: int = 24 * 3600
    max_failed_logins: int = 5
    lockout_s: int = 15 * 60
    machine_online_s: int = 120

    run_background_jobs: bool = True
    jobs_interval_s: int = 30

    log_level: str = Field(default="INFO")

    @property
    def enc_key(self) -> bytes:
        return _key32(self.data_enc_key, "DATA_ENC_KEY")

    @property
    def bidx_key(self) -> bytes:
        return _key32(self.blind_index_key, "BLIND_INDEX_KEY")

    @property
    def jwt_private_pem(self) -> bytes:
        return base64.b64decode(self.jwt_private_key_b64)

    @property
    def email_domains(self) -> set[str]:
        return {d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()}

    @property
    def allowed_origins(self) -> set[str]:
        origins = {_origin(self.frontend_base_url)}
        origins |= {_origin(o) for o in self.extra_allowed_origins.split(",") if o.strip()}
        return origins


def _key32(value: str, name: str) -> bytes:
    raw = base64.b64decode(value)
    if len(raw) != 32:
        raise ValueError(f"{name} debe ser de 32 bytes en base64")
    return raw


def _origin(url: str) -> str:
    parsed = urlparse(url.strip())
    return f"{parsed.scheme}://{parsed.netloc}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
