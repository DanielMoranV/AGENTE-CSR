"""
Controlador de Capacidades y Restricciones Operativas (AGENTE-CSR).
Verifica activamente contra 'config/capacidades.json' antes de despachar cualquier operación.
Distingue claramente entre:
1. Operación permitida y disponible.
2. Operación permitida pero sin herramienta implementada (No inventar).
3. Operación prohibida por políticas de seguridad (Rechazo explícito con auditoría).
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from src.security.audit import registrar_evento_auditoria

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_CAPACIDADES = _BASE_DIR / "config" / "capacidades.json"
if not CONFIG_CAPACIDADES.exists():
    CONFIG_CAPACIDADES = Path("C:/AGENTE-CSR/config/capacidades.json")


class CapacidadNoAutorizadaError(PermissionError):
    """Excepción para operaciones expresamente prohibidas por seguridad."""
    pass


class CapacidadNoImplementadaError(NotImplementedError):
    """Excepción para funcionalidades válidas que aún carecen de herramienta."""
    pass


class DatabaseConnectionUnavailableError(ConnectionError):
    """Excepción cuando una fuente requerida no está disponible."""
    pass


def _cargar_capacidades() -> Dict[str, Any]:
    """Carga el archivo declarativo de capacidades."""
    if not CONFIG_CAPACIDADES.exists():
        # Fallback defensivo si el archivo no existe
        return {"herramientas": {}}
    with open(CONFIG_CAPACIDADES, "r", encoding="utf-8") as f:
        return json.load(f)


def verificar_capacidad(
    nombre_herramienta: str,
    usuario: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evalúa si una herramienta está autorizada y habilitada para su ejecución.
    
    Args:
        nombre_herramienta: Identificador de la herramienta en capacidades.json
        usuario: Usuario solicitante
        
    Returns:
        Diccionario con los metadatos de la herramienta autorizada.
        
    Raises:
        CapacidadNoAutorizadaError: Si la herramienta está prohibida por seguridad.
        CapacidadNoImplementadaError: Si la herramienta no existe o no está habilitada.
    """
    catalogo = _cargar_capacidades().get("herramientas", {})
    
    if nombre_herramienta not in catalogo:
        motivo = (
            f"La herramienta '{nombre_herramienta}' no existe en el catálogo institucional. "
            "No se ejecutarán scripts nuevos ni se inventarán resultados."
        )
        registrar_evento_auditoria(
            accion="CAPACIDAD_DESCONOCIDA",
            modulo="capacidades",
            operacion=nombre_herramienta,
            detalles={"motivo": motivo},
            usuario=usuario,
            estado="BLOQUEO"
        )
        raise CapacidadNoImplementadaError(motivo)

    herramienta = catalogo[nombre_herramienta]
    habilitada = herramienta.get("habilitada", False)

    if not habilitada:
        tipo_bloqueo = herramienta.get("tipo_bloqueo", "PROHIBICION_SEGURIDAD")
        motivo = herramienta.get("motivo", "Operación no habilitada para AGENTE-CSR.")

        if tipo_bloqueo == "PROHIBICION_SEGURIDAD":
            registrar_evento_auditoria(
                accion="PROHIBICION_SEGURIDAD",
                modulo="capacidades",
                operacion=nombre_herramienta,
                detalles={"motivo": motivo},
                usuario=usuario,
                estado="BLOQUEO_SEGURIDAD"
            )
            raise CapacidadNoAutorizadaError(motivo)
        else:
            registrar_evento_auditoria(
                accion="HERRAMIENTA_FALTANTE",
                modulo="capacidades",
                operacion=nombre_herramienta,
                detalles={"motivo": motivo},
                usuario=usuario,
                estado="NO_DISPONIBLE"
            )
            raise CapacidadNoImplementadaError(motivo)

    return herramienta
