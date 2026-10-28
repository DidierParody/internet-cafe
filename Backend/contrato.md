# Contrato de Backend y Estandares de Desarrollo (BE-01) - Version 0.1

## 1. Objetivo del Modulo Backend
Establecer las directrices tecnicas, arquitectonicas y de documentacion para el desarrollo del servidor y la logica de negocio del sistema Internet Cafe, garantizando un codigo limpio, legible y estandarizado.

## 2. Estandares de Codificacion en Python
Todo el codigo desarrollado en el backend debe atenerse estrictamente a las siguientes convenciones de la comunidad Python:

- PEP 8 (Guia de estilo): Uso de snake_case para funciones y variables, CamelCase para nombres de clases, y espacios adecuados en la indentacion para asegurar la legibilidad.
- PEP 257 (Convenciones de Docstrings): Todas las clases, modulos, metodos y funciones publicas deben incluir cadenas de documentacion (docstrings) que describan claramente su comportamiento, argumentos y valores de retorno.

Ejemplo obligatorio de estructura (PEP 257):
```python
def calcular_tarifa_sesion(tiempo_minutos: int, tarifa_por_hora: float) -> float:
    """Calcula el costo total de una sesion de usuario en el internet cafe.

    Args:
        tiempo_minutos (int): Duracion total de la sesion expresada en minutos.
        tarifa_por_hora (float): Costo monetario por una hora de servicio.

    Returns:
        float: Costo total calculado y ajustado a la tarifa vigente.
    """
    return round((tiempo_minutos / 60) * tarifa_por_hora, 2)
    