"""Comandos de consola.

    uv run python -m app.cli create-admin --email admin@uni.edu.co --name "Nombre"

La contraseña se pide por consola (o se lee de ADMIN_PASSWORD).
"""

import argparse
import asyncio
import getpass
import os
import sys

from pydantic import EmailStr, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole
from app.services import users


async def create_admin(db: AsyncSession, *, email: str, full_name: str, password: str) -> User:
    email = TypeAdapter(EmailStr).validate_python(email)  # mismas reglas que el login
    if await users.exists(db, email, None):
        raise ValueError("Ya existe un usuario con ese correo")
    user = users.new_user(
        email=email,
        full_name=full_name,
        password=password,
        student_code=None,
        role=UserRole.ADMIN,
        active=True,
    )
    db.add(user)
    await db.commit()
    return user


async def _create_admin_cmd(email: str, name: str, password: str) -> None:
    from app.core.config import get_settings
    from app.core.db import Database

    database = Database(get_settings().database_url)
    try:
        async with database.sessionmaker() as db:
            await create_admin(db, email=email, full_name=name, password=password)
    finally:
        await database.dispose()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="Crea un usuario administrador")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    if args.command == "create-admin":
        password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Contraseña: ")
        if len(password) < 10:
            print("La contraseña debe tener al menos 10 caracteres", file=sys.stderr)  # noqa: T201
            return 2
        asyncio.run(_create_admin_cmd(args.email, args.name, password))
        print("Administrador creado")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
