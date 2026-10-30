"""Módulo de configuración de variables de entorno.

Valida que las llaves obligatorias existan al iniciar; si falta alguna,
el servidor se detiene automáticamente para evitar fallos de seguridad.
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password123@db:5432/internet_cafe"
    secret_key: str = "tu-llave-secreta-super-segura-123"
    app_name: str = "Internet Cafe API" 
    frontend_base_url: str = "http://localhost:5173"
    # Base del campo `type` de los errores RFC 9457 (ver app/errors.py)
    errors_base_url: str = "https://errors.internet-cafe.example"

    class Config:
        env_file = ".env"
        extra = "ignore"




# Instancia global de configuración que valida el entorno al importar el módulo
settings = Settings()