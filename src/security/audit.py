"""
Módulo de Auditoría de AGENTE-CSR (Versión 2.0).
Registra de forma persistente eventos de seguridad, consultas analíticas y exportaciones.
Captura la identidad verificable de Windows, UUID de sesión y omite datos personales o clínicos.
"""

from datetime import datetime
import json
import os
import getpass
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = (_BASE_DIR / "logs").resolve() if (_BASE_DIR / "logs").exists() else Path("C:/AGENTE-CSR/logs").resolve()
AUDIT_LOG_FILE = LOGS_DIR / "audit.log"

# Identificador único de la sesión de ejecución actual
SESION_UUID = str(uuid.uuid4())[:8]


def obtener_identidad_ejecucion() -> Dict[str, str]:
    """Obtiene la identidad real del proceso en el sistema operativo Windows."""
    try:
        usuario_os = getpass.getuser()
    except Exception:
        usuario_os = os.environ.get("USERNAME", "desconocido")

    dominio_os = os.environ.get("USERDOMAIN", "LOCAL")
    return {
        "usuario_windows": f"{dominio_os}\\{usuario_os}",
        "proceso_pid": str(os.getpid()),
        "sesion_id": SESION_UUID
    }


def registrar_evento_auditoria(
    accion: str,
    modulo: str,
    operacion: str,
    detalles: Dict[str, Any],
    usuario: Optional[str] = None,
    estado: str = "EXITO"
):
    """
    Registra un evento estructurado en el log de auditoría.
    
    Args:
        accion: Tipo de acción ('CONSULTA_INSTITUCIONAL', 'GENERACION_EXCEL', 'ACCESO_DENEGADO')
        modulo: Módulo del sistema ('database', 'reportes.excel', 'security', 'dbf_reader')
        operacion: Nombre de la operación aprobada (ej: 'facturacion_por_aseguradora')
        detalles: Metadatos analíticos (recuentos, rangos temporales). NUNCA datos de pacientes.
        usuario: Identificador de la sesión de ChatGPT o usuario informado
        estado: 'EXITO', 'ERROR' o 'BLOQUEO_SEGURIDAD'
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    identidad = obtener_identidad_ejecucion()

    # Saneamiento de detalles: nunca incluir fragmentos SQL con datos clínicos ni DNIs
    detalles_limpios = dict(detalles)
    detalles_limpios.pop("query_fragmento", None)
    detalles_limpios.pop("dni", None)
    detalles_limpios.pop("paciente", None)

    evento = {
        "timestamp": datetime.now().isoformat(),
        "identidad_os": identidad["usuario_windows"],
        "proceso_pid": identidad["proceso_pid"],
        "sesion_id": identidad["sesion_id"],
        "usuario_declarado": usuario or identidad["usuario_windows"],
        "accion": accion,
        "modulo": modulo,
        "operacion": operacion,
        "estado": estado,
        "detalles": detalles_limpios
    }

    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except Exception as e:
        # Falla crítica: si la auditoría no puede escribir, registrar en stderr
        import sys
        sys.stderr.write(f"[AUDIT FAILURE] No se pudo escribir log de auditoría: {e}\n")
