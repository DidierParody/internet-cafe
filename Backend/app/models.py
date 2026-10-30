"""Módulo de modelos de datos y roles del sistema.

Define las tablas relacionales y esquemas de la base de datos para usuarios
y la gestión de roles dentro del internet café.
"""

# Importa la clase Base declarativa desde el módulo de base de datos
from app.database import Base  # (Lo configuraremos en la tarea BE-03)
from sqlalchemy import Column, Integer, String


class RolModelo(Base):
    """Representa la tabla de roles de usuario en la base de datos."""

    # Define explícitamente el nombre de la tabla en la base de datos
    __tablename__ = "roles"

    # Identificador único de cada rol
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Nombre único que define el nivel de autorización (ej: admin, cliente, operador)
    nombre = Column(String, unique=True, index=True, nullable=False)


class UsuarioModelo(Base):
    """Representa la tabla de usuarios registrados en el sistema."""

    # Define el nombre de la tabla de usuarios
    __tablename__ = "usuarios"

    # Identificador único del usuario
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Correo electrónico único del usuario
    correo = Column(String, unique=True, index=True, nullable=False)
    
    # Rol asignado para los permisos de seguridad y acceso
    rol = Column(String, default="cliente", nullable=False)