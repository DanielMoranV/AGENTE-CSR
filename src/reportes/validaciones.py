"""
Módulo de Validaciones previas para Generación de Documentos (AGENTE-CSR).
Verifica estructura, límites de tamaño, integridad de rutas y ausencia de datos sensibles no autorizados.
"""

from pathlib import Path
import re
from typing import Dict, List, Any, Optional
import pandas as pd

from src.security.permissions import validar_ruta_escritura, SecurityViolationError, RESULTADOS_DIR


# Límites de seguridad de generación
MAX_FILAS_TABLA = 1500
MAX_CARACTERES_TEXTO = 50000


class DocumentValidationError(ValueError):
    """Excepción lanzada cuando los datos del documento no superan los controles."""
    pass


def validar_contenido_documento(
    titulo: str,
    resumen: str,
    tablas: Optional[List[Dict[str, Any]]],
    conclusiones: Optional[List[str]]
) -> None:
    """
    Valida la coherencia y límites del contenido que se plasmará en Word o PDF.
    """
    if not titulo or not titulo.strip():
        raise DocumentValidationError("El título del reporte es obligatorio y no puede estar vacío.")

    if not resumen or not resumen.strip():
        raise DocumentValidationError("El resumen ejecutivo es obligatorio.")

    if len(titulo) > 250:
        raise DocumentValidationError(f"El título excede el límite permitido ({len(titulo)} > 250).")

    if len(resumen) > MAX_CARACTERES_TEXTO:
        raise DocumentValidationError(f"El resumen excede el límite permitido ({len(resumen)} > {MAX_CARACTERES_TEXTO}).")

    # Validar tablas
    if tablas:
        for idx, item in enumerate(tablas):
            nombre_tabla = item.get("nombre", f"Tabla_{idx+1}")
            df = item.get("datos")
            if df is not None and isinstance(df, pd.DataFrame):
                if len(df) > MAX_FILAS_TABLA:
                    raise DocumentValidationError(
                        f"La tabla '{nombre_tabla}' contiene {len(df)} filas, superando el límite de {MAX_FILAS_TABLA}."
                    )

    # Validar conclusiones
    if conclusiones:
        for conc in conclusiones:
            if not isinstance(conc, str) or not conc.strip():
                raise DocumentValidationError("Cada conclusión debe ser un texto válido no vacío.")


def validar_destino_reporte(nombre_archivo: str, extension_esperada: str) -> Path:
    """
    Valida la extensión, nombre y ruta de guardado dentro de workspace/resultados/{tipo}/.
    Rechaza cualquier intento de path traversal o separadores de directorio.
    """
    if ".." in nombre_archivo or "/" in nombre_archivo or "\\" in nombre_archivo:
        raise SecurityViolationError(
            f"Intento de Path Traversal detectado en el nombre de archivo: '{nombre_archivo}'."
        )

    ext = extension_esperada.lower().lstrip(".")
    if not nombre_archivo.lower().endswith(f".{ext}"):
        nombre_archivo = f"{nombre_archivo}.{ext}"

    # Mapeo a subcarpetas de resultados estandarizadas
    carpeta_tipo = {
        "docx": "word",
        "doc": "word",
        "xlsx": "excel",
        "xls": "excel",
        "pdf": "pdf",
        "csv": "csv"
    }.get(ext, ext)

    subcarpeta = RESULTADOS_DIR / carpeta_tipo
    ruta_completa = subcarpeta / nombre_archivo
    
    # Validar contra Path Traversal con permissions.py
    return validar_ruta_escritura(ruta_completa)
