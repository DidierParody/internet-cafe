from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db

router = APIRouter(tags=["salud"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness sin acceso a base de datos (para el pinger y el health check)."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
