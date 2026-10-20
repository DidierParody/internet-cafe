import asyncio
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.helpers import admin_token, bearer, enrolled_machine, new_qr_token, student_token


async def _setup(app: object, client: AsyncClient) -> tuple[str, str, str]:
    """Devuelve (admin, machine_token, student)."""
    admin = await admin_token(app, client)
    _, machine = await enrolled_machine(client, admin)
    student = await student_token(client)
    return admin, machine, student


async def test_challenge_returns_qr_url_with_token_in_fragment(
    app: object, client: AsyncClient
) -> None:
    _, machine, _ = await _setup(app, client)
    response = await client.post("/api/v1/machine/challenges", headers=bearer(machine))
    assert response.status_code == 201
    body = response.json()
    assert body["qr_url"].startswith("https://front.example/s#")
    assert len(body["qr_url"].split("#", 1)[1]) >= 43
    assert body["rotate_after_s"] == 45
    expires = datetime.fromisoformat(body["expires_at"])
    assert timedelta(seconds=55) < expires - datetime.now(UTC) <= timedelta(seconds=60)


async def test_preview_shows_machine_without_consuming(app: object, client: AsyncClient) -> None:
    _, machine, student = await _setup(app, client)
    token = await new_qr_token(client, machine)
    for _ in range(2):
        response = await client.post(
            "/api/v1/scan/preview", headers=bearer(student), json={"token": token}
        )
        assert response.status_code == 200
        assert response.json()["machine"]["code"] == "LAB3-PC12"
        assert response.json()["machine"]["lab"] == "Sala 3"
        assert response.json()["active_session"] is None


async def test_scan_requires_student_token(app: object, client: AsyncClient) -> None:
    _, machine, _ = await _setup(app, client)
    token = await new_qr_token(client, machine)
    response = await client.post("/api/v1/scan/claim", json={"token": token})
    assert response.status_code == 401


async def test_claim_wakes_waiting_machine_with_session_data(
    app: object, client: AsyncClient
) -> None:
    _, machine, student = await _setup(app, client)
    token = await new_qr_token(client, machine)
    wait = asyncio.create_task(
        client.get("/api/v1/machine/challenges/wait?timeout=10", headers=bearer(machine))
    )
    await asyncio.sleep(0.3)
    assert not wait.done()
    claim = await client.post("/api/v1/scan/claim", headers=bearer(student), json={"token": token})
    assert claim.status_code == 201
    assert claim.json()["session"]["machine"]["code"] == "LAB3-PC12"
    assert claim.json()["session"]["status"] == "active"
    response = await asyncio.wait_for(wait, timeout=3)
    body = response.json()
    assert body["status"] == "approved"
    assert body["session"]["user"]["full_name"] == "Ana Pérez"
    assert body["session"]["user"]["student_code_masked"] == "2021****34"
    assert body["session"]["session"]["id"] == claim.json()["session"]["id"]


async def test_wait_returns_waiting_on_timeout(app: object, client: AsyncClient) -> None:
    _, machine, _ = await _setup(app, client)
    await new_qr_token(client, machine)
    response = await client.get(
        "/api/v1/machine/challenges/wait?timeout=1", headers=bearer(machine)
    )
    assert response.status_code == 200
    assert response.json() == {"status": "waiting", "session": None}


async def test_wait_sees_claim_made_before_it_started(app: object, client: AsyncClient) -> None:
    _, machine, student = await _setup(app, client)
    token = await new_qr_token(client, machine)
    await client.post("/api/v1/scan/claim", headers=bearer(student), json={"token": token})
    response = await client.get(
        "/api/v1/machine/challenges/wait?timeout=5", headers=bearer(machine)
    )
    assert response.json()["status"] == "approved"


async def test_claim_is_idempotent_for_same_user(app: object, client: AsyncClient) -> None:
    _, machine, student = await _setup(app, client)
    token = await new_qr_token(client, machine)
    first = await client.post("/api/v1/scan/claim", headers=bearer(student), json={"token": token})
    second = await client.post("/api/v1/scan/claim", headers=bearer(student), json={"token": token})
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["session"]["id"] == first.json()["session"]["id"]


async def test_used_qr_rejects_other_user(app: object, client: AsyncClient) -> None:
    _, machine, student = await _setup(app, client)
    other = await student_token(client, email="eva@uni.edu.co", code="2021005555", name="Eva Ruiz")
    token = await new_qr_token(client, machine)
    await client.post("/api/v1/scan/claim", headers=bearer(student), json={"token": token})
    response = await client.post("/api/v1/scan/claim", headers=bearer(other), json={"token": token})
    assert response.status_code == 409
    assert response.json()["code"] == "CHALLENGE_ALREADY_USED"


async def test_expired_qr_is_rejected(
    app: object, client: AsyncClient, owner_engine: AsyncEngine
) -> None:
    _, machine, student = await _setup(app, client)
    token = await new_qr_token(client, machine)
    async with owner_engine.begin() as conn:
        await conn.execute(
            sa.text("UPDATE app.login_challenges SET expires_at = :t"),
            {"t": datetime.now(UTC) - timedelta(seconds=1)},
        )
    response = await client.post(
        "/api/v1/scan/preview", headers=bearer(student), json={"token": token}
    )
    assert response.status_code == 410
    assert response.json()["code"] == "CHALLENGE_EXPIRED"


async def test_unknown_qr_is_not_found(app: object, client: AsyncClient) -> None:
    _, _, student = await _setup(app, client)
    response = await client.post(
        "/api/v1/scan/preview", headers=bearer(student), json={"token": "x" * 43}
    )
    assert response.status_code == 404
    assert response.json()["code"] == "CHALLENGE_NOT_FOUND"


async def test_rotation_keeps_at_most_two_valid_qrs(app: object, client: AsyncClient) -> None:
    _, machine, student = await _setup(app, client)
    first = await new_qr_token(client, machine)
    second = await new_qr_token(client, machine)
    third = await new_qr_token(client, machine)
    old = await client.post("/api/v1/scan/preview", headers=bearer(student), json={"token": first})
    assert old.status_code == 410
    for token in (second, third):
        ok = await client.post(
            "/api/v1/scan/preview", headers=bearer(student), json={"token": token}
        )
        assert ok.status_code == 200


async def test_approving_one_qr_cancels_the_other(app: object, client: AsyncClient) -> None:
    _, machine, student = await _setup(app, client)
    older = await new_qr_token(client, machine)
    newer = await new_qr_token(client, machine)
    await client.post("/api/v1/scan/claim", headers=bearer(student), json={"token": newer})
    response = await client.post(
        "/api/v1/scan/preview", headers=bearer(student), json={"token": older}
    )
    assert response.status_code == 410


async def test_new_machine_supersedes_previous_session(app: object, client: AsyncClient) -> None:
    admin, pc1, student = await _setup(app, client)
    _, pc2 = await enrolled_machine(client, admin, code="LAB3-PC13")
    first = await client.post(
        "/api/v1/scan/claim",
        headers=bearer(student),
        json={"token": await new_qr_token(client, pc1)},
    )
    token2 = await new_qr_token(client, pc2)
    preview = await client.post(
        "/api/v1/scan/preview", headers=bearer(student), json={"token": token2}
    )
    assert preview.json()["active_session"] == {"machine_code": "LAB3-PC12"}
    await client.post("/api/v1/scan/claim", headers=bearer(student), json={"token": token2})
    active = (await client.get("/api/v1/me/sessions/active", headers=bearer(student))).json()
    assert active["session"]["machine"]["code"] == "LAB3-PC13"
    beat = await client.post(
        "/api/v1/machine/heartbeat",
        headers=bearer(pc1),
        json={"session_id": first.json()["session"]["id"]},
    )
    assert beat.json()["session_status"] == "ended"
