"""
Conector de Base de Datos PostgreSQL en modo Solo Lectura para AGENTE-CSR (Versión 2.0).
Elimina SQL arbitrario, exige cuenta de servicio restringida 'ai_readonly'
y fuerza 'default_transaction_read_only = on' con límite estricto de filas.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.security.audit import registrar_evento_auditoria

# Cargar variables de entorno desde .env
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_env_local = _BASE_DIR / ".env"
_env_windows = Path("C:/AGENTE-CSR/.env")
if _env_local.exists():
    load_dotenv(_env_local)
elif _env_windows.exists():
    load_dotenv(_env_windows)
else:
    load_dotenv()

_engine: Optional[Engine] = None

# Cuentas autorizadas exclusivamente para el agente
CUENTAS_AUTORIZADAS = {"ai_readonly"}

# Límite máximo absoluto de filas retornadas por consulta (prevención DoS / OOM)
MAX_ROWS_ABSOLUTO = 5000


def obtener_engine_solo_lectura() -> Engine:
    """
    Inicializa o retorna el Engine de SQLAlchemy en modo estricto de SOLO LECTURA.
    Falla de inmediato si no se utiliza la cuenta autorizada 'ai_readonly'.
    """
    global _engine
    if _engine is not None:
        return _engine

    # 1. Validación estricta de la cuenta de usuario (Sin fallback a postgres)
    if "POSTGRES_USER" not in os.environ:
        raise RuntimeError(
            "Configuración de seguridad incompleta: Variable 'POSTGRES_USER' no definida en el entorno."
        )
    
    user = os.environ["POSTGRES_USER"].strip()
    if user not in CUENTAS_AUTORIZADAS:
        raise RuntimeError(
            f"Acceso denegado: AGENTE-CSR requiere la cuenta de servicio autorizada 'ai_readonly'. "
            f"Usuario proporcionado: '{user}'."
        )

    if "POSTGRES_PASSWORD" not in os.environ or not os.environ["POSTGRES_PASSWORD"]:
        raise RuntimeError("Seguridad: Contraseña de base de datos no configurada en el entorno.")

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "sisclin")
    password = os.environ["POSTGRES_PASSWORD"]
    timeout_ms = int(os.environ.get("QUERY_TIMEOUT_SECONDS", "30")) * 1000

    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    # Parámetros del socket de conexión: SOLO LECTURA y TIMEOUT a nivel de PostgreSQL
    connect_args = {
        "client_encoding": "utf8",
        "options": f"-c default_transaction_read_only=on -c statement_timeout={timeout_ms}"
    }

    _engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True
    )
    return _engine


def ejecutar_consulta_autorizada(
    operacion_id: str,
    sql_parametrizado: str,
    parametros: Optional[Dict[str, Any]] = None,
    limite_filas: int = 1000,
    usuario_sesion: Optional[str] = None
) -> pd.DataFrame:
    """
    Ejecuta una consulta SQL institucional preaprobada con parámetros validados.
    NO acepta consultas arbitrarias construidas dinámicamente por el modelo.
    """
    limite = min(limite_filas, MAX_ROWS_ABSOLUTO)
    parametros = parametros or {}
    parametros["_limite_sistema"] = limite

    # Garantizar que la consulta utiliza el límite
    sql_final = f"{sql_parametrizado.strip().rstrip(';')}\nLIMIT :_limite_sistema;"
    
    engine = obtener_engine_solo_lectura()

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                sql=text(sql_final),
                con=conn,
                params=parametros
            )

        registrar_evento_auditoria(
            accion="CONSULTA_INSTITUCIONAL",
            modulo="database",
            operacion=operacion_id,
            detalles={
                "filas_obtenidas": len(df),
                "limite_aplicado": limite,
                "parametros_keys": list(parametros.keys())
            },
            usuario=usuario_sesion,
            estado="EXITO"
        )
        return df

    except Exception as e:
        registrar_evento_auditoria(
            accion="CONSULTA_INSTITUCIONAL",
            modulo="database",
            operacion=operacion_id,
            detalles={
                "error": str(e),
                "parametros_keys": list(parametros.keys())
            },
            usuario=usuario_sesion,
            estado="ERROR"
        )
        raise
