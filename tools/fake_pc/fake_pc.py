# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.28", "qrcode[pil]>=8.0"]
# ///
"""Simulador del PC del laboratorio (PoC): reemplaza a la app de escritorio.

Hace la dinámica completa del QR contra la API: enrolamiento, QR rotativo, long-poll,
tablero de la sesión, latidos y cierre. No firma peticiones: usa el token del equipo.

Uso (desde la raíz del repo):
    uv run tools/fake_pc/fake_pc.py enroll --api http://localhost:8000 --code ABCD-EFGH
    uv run tools/fake_pc/fake_pc.py run [--open]

Durante la sesión: Enter cierra la sesión en el "PC"; Ctrl+C apaga el equipo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import qrcode

HERE = Path(__file__).resolve().parent
CONFIG = HERE / ".machine.json"
QR_PNG = HERE / "qr-actual.png"
APP_VERSION = "poc-0.1"


def log(msg: str) -> None:
    print(f"[{datetime.now().astimezone():%H:%M:%S}] {msg}", flush=True)


def load_config() -> dict[str, str]:
    if not CONFIG.exists():
        sys.exit("Este equipo no está enrolado. Ejecuta primero: fake_pc.py enroll ...")
    data: dict[str, str] = json.loads(CONFIG.read_text(encoding="utf-8"))
    return data


async def request(client: httpx.AsyncClient, method: str, url: str, **kw: Any) -> httpx.Response:
    """Reintenta con espera exponencial si la API no responde (arranque en frío de Render)."""
    delay = 2
    while True:
        try:
            return await client.request(method, url, **kw)
        except httpx.TransportError as exc:
            log(f"Conectando… ({exc.__class__.__name__}); reintento en {delay} s")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)


def show_qr(url: str, expires_at: str, open_png: bool) -> None:
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    print()
    qr.print_ascii(invert=True)
    qr.make_image().save(QR_PNG)
    log(f"QR nuevo, vence {expires_at}. También en {QR_PNG.name}")
    log(f"URL del QR: {url}")
    if open_png and hasattr(os, "startfile"):
        os.startfile(QR_PNG)  # noqa: S606 (abre el visor de imágenes en Windows)


def show_dashboard(view: dict[str, Any]) -> None:
    user, session = view["user"], view["session"]
    print("\n" + "=" * 60)
    print(f"  Bienvenido/a, {user['full_name']}  ({user['student_code_masked'] or '—'})")
    print(f"  Sesión iniciada: {session['started_at']}")
    accesses = view.get("recent_accesses") or []
    if accesses:
        print("  Últimos accesos:")
        for a in accesses:
            minutes = round((a["duration_s"] or 0) / 60)
            print(f"   - {a['machine_code']} ({a['lab'] or 'sin sala'}) · {a['started_at']} · {minutes} min")
    print("  Pulsa Enter para cerrar sesión · Ctrl+C para apagar el equipo")
    print("=" * 60 + "\n", flush=True)


async def wait_for_login(client: httpx.AsyncClient, open_png: bool) -> dict[str, Any]:
    """Muestra QR rotativos y espera con long-poll hasta que un estudiante confirme."""
    while True:
        created = await request(client, "POST", "/api/v1/machine/challenges")
        created.raise_for_status()
        challenge = created.json()
        show_qr(challenge["qr_url"], challenge["expires_at"], open_png)
        rotate_at = time.monotonic() + challenge["rotate_after_s"]
        while (remaining := rotate_at - time.monotonic()) > 0:
            timeout = max(1, min(25, int(remaining)))
            waited = await request(
                client,
                "GET",
                "/api/v1/machine/challenges/wait",
                params={"timeout": timeout},
                timeout=timeout + 10,
            )
            waited.raise_for_status()
            body = waited.json()
            if body["status"] == "approved":
                return dict(body["session"])
        log("Rotando el QR…")


def stdin_line() -> asyncio.Future[str]:
    """Lee una línea de stdin en un hilo daemon (no bloquea la salida con Ctrl+C)."""
    loop = asyncio.get_running_loop()
    future: asyncio.Future[str] = loop.create_future()

    def reader() -> None:
        line = sys.stdin.readline()
        if line == "":  # EOF: sin terminal interactiva (p. ej. en segundo plano), no es un Enter
            return
        loop.call_soon_threadsafe(lambda: future.done() or future.set_result(line))

    threading.Thread(target=reader, daemon=True).start()
    return future


async def run_session(client: httpx.AsyncClient, view: dict[str, Any]) -> str:
    """Envía latidos cada 60 s. Devuelve el motivo de fin: 'pc', 'remote' o 'shutdown'."""
    session_id = view["session"]["id"]
    enter = stdin_line()
    try:
        while True:
            done, _ = await asyncio.wait({enter}, timeout=60)
            if done:
                response = await request(
                    client, "POST", "/api/v1/machine/sessions/current/end",
                    json={"reason": "user_logout_pc"},
                )
                response.raise_for_status()
                log("Sesión cerrada desde el PC")
                return "pc"
            beat = await request(
                client, "POST", "/api/v1/machine/heartbeat",
                json={"session_id": session_id, "app_version": APP_VERSION},
            )
            beat.raise_for_status()
            if beat.json()["session_status"] != "active":
                log("La sesión se cerró de forma remota (web, admin u otro equipo)")
                return "remote"
    except asyncio.CancelledError:
        await client.post(
            "/api/v1/machine/sessions/current/end", json={"reason": "machine_shutdown"}
        )
        raise


async def run(open_png: bool) -> None:
    config = load_config()
    headers = {"Authorization": f"Bearer {config['machine_token']}"}
    async with httpx.AsyncClient(base_url=config["api"], headers=headers, timeout=40) as client:
        beat = await request(
            client, "POST", "/api/v1/machine/heartbeat", json={"app_version": APP_VERSION}
        )
        if beat.status_code != 200:
            sys.exit(f"La API rechazó el equipo: {beat.status_code} {beat.text}")
        log(f"Equipo {config['code']} conectado · modo {beat.json()['mode']}")
        while True:
            view = await wait_for_login(client, open_png)
            show_dashboard(view)
            await run_session(client, view)


async def enroll(api: str, code: str) -> None:
    async with httpx.AsyncClient(base_url=api, timeout=60) as client:
        response = await request(
            client, "POST", "/api/v1/machine/enroll",
            json={"enrollment_code": code, "hostname": os.environ.get("COMPUTERNAME", "fake-pc"),
                  "app_version": APP_VERSION},
        )
    if response.status_code != 201:
        sys.exit(f"No se pudo enrolar: {response.status_code} {response.text}")
    body = response.json()
    CONFIG.write_text(
        json.dumps({"api": api, "code": body["code"], "machine_token": body["machine_token"]}),
        encoding="utf-8",
    )
    log(f"Equipo {body['code']} enrolado (sala: {body['lab'] or '—'}). Token guardado en {CONFIG.name}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_enroll = sub.add_parser("enroll", help="Enrola este equipo con un código del panel admin")
    p_enroll.add_argument("--api", required=True, help="URL base de la API, p. ej. http://localhost:8000")
    p_enroll.add_argument("--code", required=True, help="Código de enrolamiento (XXXX-XXXX)")
    p_run = sub.add_parser("run", help="Muestra el QR y atiende sesiones")
    p_run.add_argument("--open", action="store_true", help="Abre el PNG del QR en el visor")
    args = parser.parse_args()
    try:
        if args.command == "enroll":
            asyncio.run(enroll(args.api.rstrip("/"), args.code))
        else:
            asyncio.run(run(args.open))
    except KeyboardInterrupt:
        log("Equipo apagado")


if __name__ == "__main__":
    main()
