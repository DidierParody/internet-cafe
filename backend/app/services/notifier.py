"""Avisos en memoria para el long-poll de los equipos (una sola instancia de API).

Para escalar a varias instancias, reemplazar por Postgres LISTEN/NOTIFY o Redis.
"""

import asyncio
import uuid


class MachineNotifier:
    def __init__(self) -> None:
        self._events: dict[uuid.UUID, asyncio.Event] = {}

    def subscribe(self, machine_id: uuid.UUID) -> asyncio.Event:
        """Debe llamarse ANTES de leer la base de datos para no perder avisos."""
        return self._events.setdefault(machine_id, asyncio.Event())

    def notify(self, machine_id: uuid.UUID) -> None:
        event = self._events.pop(machine_id, None)
        if event is not None:
            event.set()
