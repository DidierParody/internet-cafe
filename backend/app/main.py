"""Punto de entrada de la API: `uvicorn app.main:app`."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api import admin, auth, health, machine, me, scan
from app.core.config import get_settings
from app.core.db import Database
from app.core.errors import register_error_handlers
from app.services.notifier import MachineNotifier

API_PREFIX = "/api/v1"


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    task: asyncio.Task[None] | None = None
    if settings.run_background_jobs:
        from app.services.jobs import run_periodic_jobs

        task = asyncio.create_task(run_periodic_jobs(app))
    try:
        yield
    finally:
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await app.state.db.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app = FastAPI(
        title="Registro de acceso a equipos por QR",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.db = Database(settings.database_url)
    app.state.notifier = MachineNotifier()
    register_error_handlers(app)
    for router in (
        health.router,
        auth.router,
        me.router,
        scan.router,
        machine.router,
        admin.router,
    ):
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
