"""Tareas periódicas: cierre por inactividad y expiración de retos."""

import asyncio
import logging

from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import AccessSession, ChallengeStatus, LoginChallenge, SessionEndReason
from app.services import sessions

log = logging.getLogger(__name__)


async def close_stale_sessions(db: AsyncSession) -> int:
    limit = sessions.now() - sessions._timeout()
    stale = list(
        (
            await db.execute(
                select(AccessSession).where(
                    AccessSession.ended_at.is_(None), AccessSession.last_heartbeat_at < limit
                )
            )
        ).scalars()
    )
    for session in stale:
        sessions.end(session, SessionEndReason.HEARTBEAT_TIMEOUT)
    await db.commit()
    return len(stale)


async def expire_challenges(db: AsyncSession) -> int:
    result = await db.execute(
        update(LoginChallenge)
        .where(
            LoginChallenge.status == ChallengeStatus.PENDING,
            LoginChallenge.expires_at <= sessions.now(),
        )
        .values(status=ChallengeStatus.EXPIRED)
    )
    await db.commit()
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


async def run_periodic_jobs(app: FastAPI) -> None:
    interval = get_settings().jobs_interval_s
    while True:
        try:
            async with app.state.db.sessionmaker() as db:
                closed = await close_stale_sessions(db)
                expired = await expire_challenges(db)
            if closed or expired:
                log.info("jobs: %s sesiones cerradas, %s retos expirados", closed, expired)
        except Exception:
            log.exception("Fallo en las tareas periódicas")
        await asyncio.sleep(interval)
