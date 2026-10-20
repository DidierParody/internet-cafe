import re
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.helpers import admin_token, bearer, enrolled_machine, student_token


async def test_admin_endpoints_require_admin_role(client: AsyncClient) -> None:
    token = await student_token(client)
    response = await client.get("/api/v1/admin/labs", headers=bearer(token))
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


async def test_admin_creates_lab_machine_and_enrollment_code(
    app: object, client: AsyncClient
) -> None:
    admin = await admin_token(app, client)
    lab = await client.post(
        "/api/v1/admin/labs", headers=bearer(admin), json={"name": "Sala 3", "building": "Bloque B"}
    )
    assert lab.status_code == 201
    machine = await client.post(
        "/api/v1/admin/machines",
        headers=bearer(admin),
        json={"code": "LAB3-PC12", "lab_id": lab.json()["id"], "mode": "kiosk"},
    )
    assert machine.status_code == 201
    assert machine.json()["status"] == "pending_enrollment"
    assert machine.json()["lab"] == "Sala 3"
    code = await client.post(
        f"/api/v1/admin/machines/{machine.json()['id']}/enrollment-codes", headers=bearer(admin)
    )
    assert code.status_code == 201
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", code.json()["code"])


async def test_duplicate_machine_code_is_rejected(app: object, client: AsyncClient) -> None:
    admin = await admin_token(app, client)
    await client.post("/api/v1/admin/machines", headers=bearer(admin), json={"code": "PC-1"})
    again = await client.post(
        "/api/v1/admin/machines", headers=bearer(admin), json={"code": "PC-1"}
    )
    assert again.status_code == 409


async def test_enrollment_code_is_single_use(app: object, client: AsyncClient) -> None:
    admin = await admin_token(app, client)
    machine = await client.post(
        "/api/v1/admin/machines", headers=bearer(admin), json={"code": "PC-1"}
    )
    mid = machine.json()["id"]
    code = (
        await client.post(f"/api/v1/admin/machines/{mid}/enrollment-codes", headers=bearer(admin))
    ).json()["code"]
    first = await client.post("/api/v1/machine/enroll", json={"enrollment_code": code.lower()})
    assert first.status_code == 201
    assert first.json()["machine_token"]
    assert first.json()["code"] == "PC-1"
    second = await client.post("/api/v1/machine/enroll", json={"enrollment_code": code})
    assert second.status_code == 401
    assert second.json()["code"] == "ENROLLMENT_CODE_INVALID"


async def test_expired_enrollment_code_is_rejected(
    app: object, client: AsyncClient, owner_engine: AsyncEngine
) -> None:
    admin = await admin_token(app, client)
    machine = await client.post(
        "/api/v1/admin/machines", headers=bearer(admin), json={"code": "PC-1"}
    )
    mid = machine.json()["id"]
    code = (
        await client.post(f"/api/v1/admin/machines/{mid}/enrollment-codes", headers=bearer(admin))
    ).json()["code"]
    async with owner_engine.begin() as conn:
        await conn.execute(
            sa.text("UPDATE app.enrollment_codes SET expires_at = :t"),
            {"t": datetime.now(UTC) - timedelta(minutes=1)},
        )
    response = await client.post("/api/v1/machine/enroll", json={"enrollment_code": code})
    assert response.status_code == 401


async def test_machine_endpoints_require_machine_token(client: AsyncClient) -> None:
    response = await client.post("/api/v1/machine/challenges")
    assert response.status_code == 401
    bad = await client.post("/api/v1/machine/challenges", headers=bearer("token-falso"))
    assert bad.status_code == 401


async def test_disabled_machine_is_rejected(app: object, client: AsyncClient) -> None:
    admin = await admin_token(app, client)
    machine_id, token = await enrolled_machine(client, admin)
    patch = await client.patch(
        f"/api/v1/admin/machines/{machine_id}", headers=bearer(admin), json={"status": "disabled"}
    )
    assert patch.status_code == 200
    response = await client.post("/api/v1/machine/challenges", headers=bearer(token))
    assert response.status_code == 403
    assert response.json()["code"] == "MACHINE_DISABLED"


async def test_admin_lists_machines_with_online_state(app: object, client: AsyncClient) -> None:
    admin = await admin_token(app, client)
    _, token = await enrolled_machine(client, admin)
    await client.post("/api/v1/machine/heartbeat", headers=bearer(token), json={})
    machines = (await client.get("/api/v1/admin/machines", headers=bearer(admin))).json()
    assert machines[0]["code"] == "LAB3-PC12"
    assert machines[0]["status"] == "active"
    assert machines[0]["online"] is True
