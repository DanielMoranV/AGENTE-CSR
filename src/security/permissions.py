"""
Módulo de Seguridad y Permisos para AGENTE-CSR (Versión 2.0 - Endurecida).
Garantiza el aislamiento de rutas, sanitización de datos y rechazo de symlinks.
"""

from pathlib import Path
import os
from typing import Any, Union


# Ruta base del proyecto (detectada dinámicamente para compatibilidad con Windows y Linux/WSL)
_dir_origen = Path(__file__).resolve().parent.parent.parent
BASE_DIR = _dir_origen if _dir_origen.exists() else Path("C:/AGENTE-CSR").resolve()
WORKSPACE_DIR = (BASE_DIR / "workspace").resolve()
RESULTADOS_DIR = (WORKSPACE_DIR / "resultados").resolve()
TEMPORALES_DIR = (WORKSPACE_DIR / "temporales").resolve()


class SecurityViolationError(PermissionError):
    """Excepción lanzada cuando una operación viola las políticas de seguridad."""
    pass


def validar_ruta_escritura(ruta_destino: Union[str, Path]) -> Path:
    """
    Verifica que la ruta destino resida estrictamente dentro de workspace/.
    Previene vulnerabilidades de Path Traversal y enlaces simbólicos/junctions.
    """
    # Normalización para compatibilidad Windows / Linux
    path_str = str(ruta_destino).replace("\\", "/")
    if os.name != "nt" and (path_str.startswith("C:/AGENTE-CSR/") or path_str == "C:/AGENTE-CSR"):
        rel = path_str[len("C:/AGENTE-CSR/"):].lstrip("/")
        path_obj = BASE_DIR / rel if rel else BASE_DIR
    else:
        path_obj = Path(ruta_destino)
    
    # 1. Resolver ruta canónica absoluta
    try:
        path_resuelto = path_obj.resolve()
    except Exception as e:
        raise SecurityViolationError(f"Ruta inválida o ininteligible: {e}")

    # 2. Comprobar que path_resuelto está contenido en WORKSPACE_DIR
    try:
        path_resuelto.relative_to(WORKSPACE_DIR)
    except ValueError:
        raise SecurityViolationError(
            f"Acceso denegado: El intento de escribir en '{path_resuelto}' "
            f"está fuera del espacio de trabajo autorizado ({WORKSPACE_DIR})."
        )
    
    # 3. Protección contra Symlinks y Junctions en Windows
    # Si alguna parte del árbol existente es un enlace simbólico, abortar.
    actual = path_resuelto
    while actual != WORKSPACE_DIR and actual != actual.parent:
        if actual.exists() and actual.is_symlink():
            raise SecurityViolationError(
                f"Acceso denegado: Se detectó enlace simbólico en '{actual}'."
            )
        actual = actual.parent

    # 4. Asegurar que el directorio padre existe
    path_resuelto.parent.mkdir(parents=True, exist_ok=True)
    return path_resuelto


def sanitizar_valor_excel(valor: Any) -> Any:
    """
    Previene inyección de fórmulas en hojas de cálculo (CSV/Excel Formula Injection).
    Neutraliza celdas de texto que inicien con '=', '+', '-', '@', tabulaciones o retornos.
    """
    if isinstance(valor, str):
        caracteres_peligrosos = ('=', '+', '-', '@', '\t', '\r')
        if valor.startswith(caracteres_peligrosos):
            # Prevenir ejecución de macros o comandos anteponiendo comilla simple
            return f"'{valor}"
    return valor
