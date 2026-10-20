"""Hash de contraseñas con Argon2id (parámetros recomendados por OWASP)."""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_hasher = PasswordHash((Argon2Hasher(time_cost=2, memory_cost=19456, parallelism=1),))

# Hash fijo para igualar tiempos cuando el usuario no existe (evita enumeración por tiempo).
DUMMY_HASH = _hasher.hash("contraseña-de-relleno-para-tiempos")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _hasher.verify(password, hashed)
