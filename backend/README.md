# API · Registro de acceso a equipos por QR (PoC)

FastAPI + SQLAlchemy 2 (async, asyncpg) + Alembic sobre PostgreSQL (Neon). Implementa el
flujo QR del SRS (`docs/srs/`) con estos recortes de PoC:

- **El equipo no firma peticiones:** se autentica con un token Bearer que recibe al enrolarse. En el MVP se reemplaza por RFC 9421.
- **Sin correo:** las cuentas quedan activas al registrarse (`require_email_verification=false`).
- **Dos roles de base de datos:** el owner (solo migraciones) y `svc_app` (runtime, sin DDL ni DELETE sobre datos de negocio). Los roles por actor y la RLS quedan para el MVP.

## Requisitos

- Python 3.12 y [uv](https://docs.astral.sh/uv/)
- Docker (solo para las pruebas: levantan PostgreSQL 18 con testcontainers)

## Puesta en marcha local

```bash
uv sync
cp .env.example .env              # completa los valores
uv run python -m app.keys         # genera llaves para el .env
uv run python -m app.db_admin bootstrap-role   # crea/actualiza el rol svc_app (usa el owner)
uv run python -m app.db_admin migrate          # aplica las migraciones (usa el owner)
uv run python -m app.cli create-admin --email tu@correo.com --name "Tu nombre"
uv run uvicorn app.main:app --reload
```

- Documentación interactiva: http://localhost:8000/api/docs
- Salud: `GET /api/v1/healthz` (sin BD) y `GET /api/v1/readyz` (con BD).

## Pruebas y calidad

```bash
uv run pytest            # 63 pruebas contra PostgreSQL 18 en Docker
uv run ruff check . && uv run ruff format --check .
uv run mypy app
```

## Migraciones

- Se escriben con Alembic en `migrations/versions/` y **siempre** se ejecutan con el owner (`DATABASE_URL_MIGRATIONS`, host directo sin `-pooler`).
- La API nunca tiene esa credencial.
- Para crear una migración nueva: `uv run alembic revision --autogenerate -m "descripcion"`.

## Despliegue en Render

1. En Render, crea un *Blueprint* apuntando a este repositorio. Usa `render.yaml` de la raíz: servicio web gratuito en Ohio, raíz `backend/`, `uvicorn` con 1 worker y health check en `/api/v1/healthz`.
2. Carga las variables marcadas `sync: false`. Toma los valores de tu `backend/.env`:
   - `DATABASE_URL`: rol `svc_app` con el host `-pooler`.
   - `DATA_ENC_KEY`, `BLIND_INDEX_KEY` y `JWT_PRIVATE_KEY_B64`: **las mismas** que usaste localmente contra esa base. Si cambian, los datos cifrados no se pueden leer.
   - `FRONTEND_BASE_URL`: la URL de Vercel cuando exista (mientras tanto, `http://localhost:5173`).
   - `ALLOWED_EMAIL_DOMAINS`: los dominios institucionales, o vacío para aceptar cualquiera.
3. **No** cargues `DATABASE_URL_MIGRATIONS` ni `APP_DB_PASSWORD` en Render.
4. Aplica las migraciones desde tu máquina antes de desplegar un cambio de esquema.

## Simulador del PC

Ver `tools/fake_pc/README.md`.
