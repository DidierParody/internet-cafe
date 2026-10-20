"""Utilidades compartidas por las pruebas de la API."""

from typing import Any

from httpx import AsyncClient

DEFAULT_PASSWORD = "clave-de-prueba-123"


async def register(
    client: AsyncClient,
    email: str = "ana@uni.edu.co",
    code: str = "2021001234",
    name: str = "Ana Pérez",
    password: str = DEFAULT_PASSWORD,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "student_code": code,
            "full_name": name,
            "password": password,
            "privacy_consent": True,
        },
    )
    assert response.status_code == 202, response.text


async def login(
    client: AsyncClient, email: str = "ana@uni.edu.co", password: str = DEFAULT_PASSWORD
) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def student_token(client: AsyncClient, email: str = "ana@uni.edu.co", **kw: str) -> str:
    await register(client, email=email, **kw)
    body = await login(client, email=email)
    token: str = body["access_token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


ADMIN_EMAIL = "admin@uni.edu.co"
ADMIN_PASSWORD = "clave-admin-segura-1"


async def admin_token(app: Any, client: AsyncClient) -> str:
    """Crea un administrador con la misma función que usa la CLI e inicia sesión."""
    from app.cli import create_admin

    async with app.state.db.sessionmaker() as db:
        await create_admin(db, email=ADMIN_EMAIL, full_name="Admin Sala", password=ADMIN_PASSWORD)
    body = await login(client, email=ADMIN_EMAIL, password=ADMIN_PASSWORD)
    token: str = body["access_token"]
    return token


async def enrolled_machine(
    client: AsyncClient, admin: str, code: str = "LAB3-PC12", lab_name: str = "Sala 3"
) -> tuple[str, str]:
    """Crea sala y equipo, genera el código y enrola. Devuelve (machine_id, machine_token)."""
    labs = (await client.get("/api/v1/admin/labs", headers=bearer(admin))).json()
    lab = next((x for x in labs if x["name"] == lab_name), None)
    if lab is None:
        lab = (
            await client.post("/api/v1/admin/labs", headers=bearer(admin), json={"name": lab_name})
        ).json()
    machine = await client.post(
        "/api/v1/admin/machines", headers=bearer(admin), json={"code": code, "lab_id": lab["id"]}
    )
    assert machine.status_code == 201, machine.text
    machine_id = machine.json()["id"]
    enrollment = await client.post(
        f"/api/v1/admin/machines/{machine_id}/enrollment-codes", headers=bearer(admin)
    )
    assert enrollment.status_code == 201, enrollment.text
    enrolled = await client.post(
        "/api/v1/machine/enroll",
        json={"enrollment_code": enrollment.json()["code"], "hostname": "pc-12"},
    )
    assert enrolled.status_code == 201, enrolled.text
    token: str = enrolled.json()["machine_token"]
    return machine_id, token


async def new_qr_token(client: AsyncClient, machine_token: str) -> str:
    response = await client.post("/api/v1/machine/challenges", headers=bearer(machine_token))
    assert response.status_code == 201, response.text
    url: str = response.json()["qr_url"]
    return url.split("#", 1)[1]
