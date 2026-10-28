"""Módulo de auditoría para el sistema (SRS Sección 11.2).

Proporciona la función helper audit() para registrar acciones en la base de datos
sin acoplar esta lógica a los modelos ORM.
"""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditLog, AuditActorType

async def audit(
    db: AsyncSession, 
    actor_type: AuditActorType, 
    action: str, 
    actor_id: uuid.UUID = None, 
    target_type: str = None, 
    target_id: uuid.UUID = None, 
    metadata_info: dict = None
):
    """
    Helper para registrar una acción en el log de auditoría.
    
    Args:
        db: La sesión activa de la base de datos.
        actor_type: Quién realiza la acción (user, machine, system).
        action: Nombre de la acción (ej. 'user.login').
        actor_id: UUID de quien actúa.
        target_type: Tipo de objeto afectado (ej. 'session').
        target_id: UUID del objeto afectado.
        metadata_info: Datos adicionales sin PII.
    """
    log_entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_info=metadata_info
    )
    db.add(log_entry)
    # El commit se hace en el endpoint que llama a esta función para mantener la transacción atómica.