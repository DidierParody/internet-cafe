import pytest
from httpx import AsyncClient
from freezegun import freeze_time
from app.main import app


@pytest.fixture
async def async_client():
    """Cliente HTTP asíncrono para pruebas de integración."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def frozen_clock():
    """Dispositivo de reloj controlable con freezegun."""
    with freeze_time("2026-10-28 10:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture(autouse=True)
def db_cleanup():
    """Limpieza de base de datos usando TRUNCATE."""
    yield