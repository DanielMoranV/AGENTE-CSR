"""
Herramientas autorizadas de Lectura Directa de Archivos DBF (SISCLIN y SISLAB).
Acceso estrictamente de SOLO LECTURA binaria ('rb') sin bloqueo de concurrencia.
"""

import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, date
import pandas as pd

from src.dbf_reader.foxpro_reader import FoxProDbfReader
from src.security.audit import registrar_evento_auditoria


def _obtener_ruta_carpeta_dbf(tipo_fuente: str = "sisclin") -> Path:
    """Valida y retorna la ruta de red o local de la carpeta DBF."""
    variable = "DBF_FOLDER_PATH" if tipo_fuente == "sisclin" else "SISLAB_DBF_FOLDER_PATH"
    _BASE_DIR = Path(__file__).resolve().parent.parent.parent
    
    # En Linux / WSL, buscar si existe ruta montada vía _LINUX
    if os.name != "nt":
        ruta_linux = os.environ.get(f"{variable}_LINUX", "")
        if ruta_linux and Path(ruta_linux).exists():
            return Path(ruta_linux)

    ruta_str = os.environ.get(variable, "")
    
    if not ruta_str:
        # Fallback a carpeta local DATA de prueba si no hay ruta de red configurada
        ruta_local = _BASE_DIR / "workspace" / "temporales" / "datos_prueba"
        ruta_local.mkdir(parents=True, exist_ok=True)
        return ruta_local
        
    path = Path(ruta_str)
    if not path.exists():
        # Si la ruta UNC Windows no es accesible directamente en Linux/WSL,
        # verificar carpeta local de pruebas antes de fallar
        ruta_local = _BASE_DIR / "workspace" / "temporales" / "datos_prueba"
        if ruta_local.exists():
            return ruta_local
        raise FileNotFoundError(f"Carpeta de datos {tipo_fuente} no accesible: {path}")
    return path


def consultar_dbf_admisiones_recientes(
    limite: int = 100,
    usuario_sesion: Optional[str] = None
) -> pd.DataFrame:
    """
    Lee las admisiones recientes directamente del archivo sc0011.DBF (SISCLIN) en caliente.
    Utiliza FoxProDbfReader en modo 'rb' sin alterar el archivo original.
    """
    carpeta = _obtener_ruta_carpeta_dbf("sisclin")
    archivo_dbf = carpeta / "sc0011.DBF"
    if not archivo_dbf.exists():
        # Intentar en minúsculas por compatibilidad
        archivo_dbf = carpeta / "sc0011.dbf"

    if not archivo_dbf.exists():
        # Si no existe archivo físico en el entorno de desarrollo, devolver estructura vacía o sintética
        return pd.DataFrame(columns=["id_doc", "fecha_ingreso", "tipo_atencion", "id_cia", "estado"])

    encoding = os.environ.get("DBF_ENCODING", "cp1252")
    registros = []

    try:
        with FoxProDbfReader(str(archivo_dbf), encoding=encoding) as reader:
            for rec in reader.read_all_records(load_deleted=False):
                # Extraer únicamente campos analíticos generales (sin nombres de personas)
                datos = rec.to_dict()
                registros.append({
                    "id_doc": datos.get("NUM_DOC") or datos.get("ID_DOC"),
                    "fecha_ingreso": datos.get("FEC_ING"),
                    "tipo_atencion": datos.get("TIP_ATE"),
                    "id_cia": datos.get("ID_CIA"),
                    "estado": datos.get("ESTADO")
                })
                if len(registros) >= limite:
                    break

        df = pd.DataFrame(registros)
        registrar_evento_auditoria(
            accion="LECTURA_DBF_DIRECTA",
            modulo="dbf_reader",
            operacion="admisiones_sc0011",
            detalles={"archivo": "sc0011.DBF", "registros_leidos": len(df)},
            usuario=usuario_sesion,
            estado="EXITO"
        )
        return df

    except Exception as e:
        registrar_evento_auditoria(
            accion="LECTURA_DBF_DIRECTA",
            modulo="dbf_reader",
            operacion="admisiones_sc0011",
            detalles={"error": str(e), "archivo": "sc0011.DBF"},
            usuario=usuario_sesion,
            estado="ERROR"
        )
        raise


def consultar_dbf_ordenes_recientes(
    limite: int = 100,
    usuario_sesion: Optional[str] = None
) -> pd.DataFrame:
    """
    Lee las órdenes recientes de laboratorio directamente de SC0020.DBF (SISLAB).
    Solo lectura en flujo binario 'rb'.
    """
    carpeta = _obtener_ruta_carpeta_dbf("sislab")
    archivo_dbf = carpeta / "SC0020.DBF"
    if not archivo_dbf.exists():
        archivo_dbf = carpeta / "sc0020.dbf"

    if not archivo_dbf.exists():
        return pd.DataFrame(columns=["orden_id", "fecha_orden", "origen", "estado"])

    encoding = os.environ.get("SISLAB_DBF_ENCODING", "latin-1")
    registros = []

    try:
        with FoxProDbfReader(str(archivo_dbf), encoding=encoding) as reader:
            for rec in reader.read_all_records(load_deleted=False):
                datos = rec.to_dict()
                registros.append({
                    "orden_id": datos.get("NUM_ORD") or datos.get("ORDEN_ID"),
                    "fecha_orden": datos.get("FEC_ORD"),
                    "origen": datos.get("ORIGEN"),
                    "estado": datos.get("ESTADO")
                })
                if len(registros) >= limite:
                    break

        df = pd.DataFrame(registros)
        registrar_evento_auditoria(
            accion="LECTURA_DBF_DIRECTA",
            modulo="dbf_reader",
            operacion="ordenes_sc0020",
            detalles={"archivo": "SC0020.DBF", "registros_leidos": len(df)},
            usuario=usuario_sesion,
            estado="EXITO"
        )
        return df

    except Exception as e:
        registrar_evento_auditoria(
            accion="LECTURA_DBF_DIRECTA",
            modulo="dbf_reader",
            operacion="ordenes_sc0020",
            detalles={"error": str(e), "archivo": "SC0020.DBF"},
            usuario=usuario_sesion,
            estado="ERROR"
        )
        raise
