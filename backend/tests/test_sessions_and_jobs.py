from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services import jobs
from tests.helpers import admin_token, bearer, enrolled_machine, new_qr_token, student_token


async def _session(app: object, client: AsyncClient) -> tuple[str, str, str, str]:
    """Crea un acceso activo. Devuelve (admin, machine_token, student, session_id)."""
    admin = await admin_token(app, client)
    _, machine = await enrolled_machine(client, admin)
    student = await student_token(client)
    claim = await client.post(
        "/api/v1/scan/claim",
        headers=bearer(student),
        json={"token": await new_qr_token(client, machine)},
    )
    return admin, machine, student, claim.json()["session"]["id"]


async def test_heartbeat_reports_active_session(app: object, client: AsyncClient) -> None:
    _, machine, _, session_id = await _session(app, client)
    response = await client.post(
        "/api/v1/machine/heartbeat", headers=bearer(machine), json={"session_id": session_id}
    )
    assert response.status_code == 200
    assert response.json()["session_status"] == "active"
    assert response.json()["mode"] == "passive"


async def test_machine_current_session_and_end(app: object, client: AsyncClient) -> None:
    _, machine, student, _ = await _session(app, client)
    current = await client.get("/api/v1/machine/sessions/current", headers=bearer(machine))
    assert current.status_code == 200
    assert current.json()["user"]["full_name"] == "Ana Pérez"
    end = await client.post(
        "/api/v1/machine/sessions/current/end", headers=bearer(machine), json={}
    )
    assert end.status_code == 200
    assert (
        await client.get("/api/v1/machine/sessions/current", headers=bearer(machine))
    ).status_code == 204
    history = (await client.get("/api/v1/me/sessions", headers=bearer(student))).json()
    assert history["items"][0]["end_reason"] == "user_logout_pc"


async def test_student_ends_session_from_web(app: object, client: AsyncClient) -> None:
    _, machine, student, session_id = await _session(app, client)
    response = await client.post(f"/api/v1/me/sessions/{session_id}/end", headers=bearer(student))
    assert response.status_code == 200
    assert response.json()["status"] == "ended"
    beat = await client.post(
        "/api/v1/machine/heartbeat", headers=bearer(machine), json={"session_id": session_id}
    )
    assert beat.json()["session_status"] == "ended"
    assert (await client.get("/api/v1/me/sessions/active", headers=bearer(student))).json() == {
        "session": None
    }


async def test_student_cannot_end_someone_elses_session(app: object, client: AsyncClient) -> None:
    _, _, _, session_id = await _session(app, client)
    other = await student_token(client, email="eva@uni.edu.co", code="2021005555", name="Eva Ruiz")
    response = await client.post(f"/api/v1/me/sessions/{session_id}/end", headers=bearer(other))
    assert response.status_code == 404
    assert response.json()["code"] == "SESSION_NOT_FOUND"


async def test_new_challenge_closes_orphan_session_of_machine(
    app: object, client: AsyncClient
) -> None:
    _, machine, student, _ = await _session(app, client)
    await new_qr_token(client, machine)  # el PC se reinició y volvió a pedir QR
    history = (await client.get("/api/v1/me/sessions", headers=bearer(student))).json()
    assert history["items"][0]["status"] == "ended"
    assert history["items"][0]["end_reason"] == "superseded"


async def test_session_history_is_paginated(app: object, client: AsyncClient) -> None:
    admin = await admin_token(app, client)
    _, machine = await enrolled_machine(client, admin)
    student = await student_token(client)
    for _ in range(3):
        await client.post(
            "/api/v1/scan/claim",
            headers=bearer(student),
            json={"token": await new_qr_token(client, machine)},
        )
        await client.post("/api/v1/machine/sessions/current/end", headers=bearer(machine), json={})
    first = (await client.get("/api/v1/me/sessions?limit=2", headers=bearer(student))).json()
    assert len(first["items"]) == 2
    assert first["next_cursor"]
    second = (
        await client.get(
            f"/api/v1/me/sessions?limit=2&cursor={first['next_cursor']}", headers=bearer(student)
        )
    ).json()
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None
    ids = [s["id"] for s in first["items"] + second["items"]]
    assert len(set(ids)) == 3


async def test_recent_accesses_show_previous_sessions(app: object, client: AsyncClient) -> None:
    admin = await admin_token(app, client)
    _, machine = await enrolled_machine(client, admin)
    student = await student_token(client)
    for _ in range(2):
        await client.post(
            "/api/v1/scan/claim",
            headers=bearer(student),
            json={"token": await new_qr_token(client, machine)},
        )
    await client.post("/api/v1/machine/sessions/current/end", headers=bearer(machine), json={})
    await client.post(
        "/api/v1/scan/claim",
        headers=bearer(student),
        json={"token": await new_qr_token(client, machine)},
    )
    current = (await client.get("/api/v1/machine/sessions/current", headers=bearer(machine))).json()
    assert len(current["recent_accesses"]) == 2
    assert current["recent_accesses"][0]["machine_code"] == "LAB3-PC12"


async def test_admin_lists_and_force_ends_sessions(app: object, client: AsyncClient) -> None:
    admin, machine, _, session_id = await _session(app, client)
    listed = (await client.get("/api/v1/admin/sessions?active=true", headers=bearer(admin))).json()
    assert listed["items"][0]["id"] == session_id
    assert listed["items"][0]["student_name"] == "Ana Pérez"
    forced = await client.post(f"/api/v1/admin/sessions/{session_id}/end", headers=bearer(admin))
    assert forced.status_code == 200
    assert forced.json()["end_reason"] == "admin_forced"
    beat = await client.post(
        "/api/v1/machine/heartbeat", headers=bearer(machine), json={"session_id": session_id}
    )
    assert beat.json()["session_status"] == "ended"


async def test_stale_session_is_closed_at_last_heartbeat(
    app: object, client: AsyncClient, owner_engine: AsyncEngine
) -> None:
    _, _, student, _ = await _session(app, client)
    last = datetime.now(UTC) - timedelta(minutes=10)
    async with owner_engine.begin() as conn:
        await conn.execute(
            sa.text("UPDATE app.access_sessions SET started_at = :s, last_heartbeat_at = :t"),
            {"s": last - timedelta(minutes=5), "t": last},
        )
    async with app.state.db.sessionmaker() as db:  # type: ignore[attr-defined]
        closed = await jobs.close_stale_sessions(db)
    assert closed == 1
    item = (await client.get("/api/v1/me/sessions", headers=bearer(student))).json()["items"][0]
    assert item["end_reason"] == "heartbeat_timeout"
    assert datetime.fromisoformat(item["ended_at"]) == last.replace(microsecond=last.microsecond)


async def test_expired_challenges_are_marked(
    app: object, client: AsyncClient, owner_engine: AsyncEngine
) -> None:
    admin = await admin_token(app, client)
    _, machine = await enrolled_machine(client, admin)
    await new_qr_token(client, machine)
    async with owner_engine.begin() as conn:
        await conn.execute(
            sa.text("UPDATE app.login_challenges SET expires_at = :t"),
            {"t": datetime.now(UTC) - timedelta(seconds=5)},
        )
    async with app.state.db.sessionmaker() as db:  # type: ignore[attr-defined]
        assert await jobs.expire_challenges(db) == 1
    async with owner_engine.connect() as conn:
        status = (
            await conn.execute(sa.text("SELECT status FROM app.login_challenges"))
        ).scalar_one()
    assert status == "expired"
