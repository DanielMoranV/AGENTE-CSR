"""
Suite de Pruebas Automatizadas de Seguridad y Controles para AGENTE-CSR.
Verifica:
1. Bloqueo estricto de Path Traversal y escrituras fuera de workspace/.
2. Sanitización contra inyección de fórmulas de Excel.
3. Rechazo de cuentas no autorizadas (ej. postgres) en el conector DB.
4. Auditoría estructurada sin fuga de datos sensibles.
5. Catálogo de consultas preaprobadas con parámetros seguros.
"""

import os
import sys
from pathlib import Path
import pytest
import pandas as pd

# Asegurar importación de la raíz del proyecto
_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ))

from src.security.permissions import (
    validar_ruta_escritura,
    sanitizar_valor_excel,
    SecurityViolationError,
    WORKSPACE_DIR
)
from src.database.connection import obtener_engine_solo_lectura
from src.security.audit import registrar_evento_auditoria, AUDIT_LOG_FILE
from src.consultas.facturacion import (
    consultar_facturacion_por_aseguradora,
    comparar_facturacion_periodos
)


# ==============================================================
# 1. PRUEBAS DE AISLAMIENTO DE RUTAS (PATH TRAVERSAL)
# ==============================================================

def test_permitir_escritura_dentro_de_workspace():
    """Valida que una ruta legítima en workspace/ sea aceptada."""
    ruta_valida = WORKSPACE_DIR / "resultados" / "excel" / "test_reporte.xlsx"
    resuelto = validar_ruta_escritura(ruta_valida)
    assert resuelto == ruta_valida.resolve()


def test_bloquear_escritura_fuera_de_workspace():
    """Valida que cualquier intento de escribir fuera de workspace/ sea bloqueado."""
    rutas_maliciosas = [
        Path("C:/Windows/System32/drivers/etc/hosts"),
        Path("C:/AGENTE-CSR/src/hack.py"),
        Path("C:/AGENTE-CSR/instrucciones/agente.md"),
        Path("C:/AGENTE-CSR/workspace/../../autoexec.bat"),
        Path("C:/AGENTE-CSR/.env")
    ]
    for ruta in rutas_maliciosas:
        with pytest.raises(SecurityViolationError):
            validar_ruta_escritura(ruta)


# ==============================================================
# 2. PRUEBAS DE SANITIZACIÓN DE FÓRMULAS EXCEL
# ==============================================================

def test_sanitizar_formula_injection():
    """Valida que caracteres disparadores de fórmulas sean neutralizados."""
    assert sanitizar_valor_excel("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
    assert sanitizar_valor_excel("+123456789") == "'+123456789"
    assert sanitizar_valor_excel("-SUM(1,2)") == "'-SUM(1,2)"
    assert sanitizar_valor_excel("@SUM(1,2)") == "'@SUM(1,2)"
    assert sanitizar_valor_excel("\tTexto") == "'\tTexto"


def test_no_alterar_valores_legitimos():
    """Valida que datos numéricos y textos normales no se modifiquen."""
    assert sanitizar_valor_excel(12345) == 12345
    assert sanitizar_valor_excel(45.67) == 45.67
    assert sanitizar_valor_excel("PACIFICO SEGUROS") == "PACIFICO SEGUROS"
    assert sanitizar_valor_excel("RIMAC EPS") == "RIMAC EPS"


# ==============================================================
# 3. PRUEBAS DE RECHAZO DE CUENTAS NO AUTORIZADAS
# ==============================================================

def test_rechazo_usuario_postgres_predeterminado(monkeypatch):
    """Verifica que el sistema rechace conectarse como superusuario 'postgres'."""
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    
    # Reiniciar engine singleton para la prueba
    import src.database.connection as conn_mod
    conn_mod._engine = None

    with pytest.raises(RuntimeError, match="requiere la cuenta de servicio autorizada"):
        obtener_engine_solo_lectura()


def test_rechazo_cuando_falta_usuario_en_entorno(monkeypatch):
    """Verifica que no exista fallback silencioso si falta POSTGRES_USER."""
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    
    import src.database.connection as conn_mod
    conn_mod._engine = None

    with pytest.raises(RuntimeError, match="Variable 'POSTGRES_USER' no definida"):
        obtener_engine_solo_lectura()


# ==============================================================
# 4. PRUEBAS DE AUDITORÍA SIN DATOS SENSIBLES
# ==============================================================

def test_auditoria_omite_datos_clinicos_y_dnis():
    """Verifica que la auditoría no registre DNIs ni fragmentos SQL crudos."""
    registrar_evento_auditoria(
        accion="PRUEBA_SEGURIDAD",
        modulo="test",
        operacion="test_operacion",
        detalles={
            "query_fragmento": "SELECT * FROM pacientes WHERE dni = '12345678'",
            "dni": "12345678",
            "paciente": "JUAN PEREZ",
            "recuento": 10
        },
        usuario="Auditor_Test"
    )

    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        ultima_linea = f.readlines()[-1]

    assert "12345678" not in ultima_linea
    assert "JUAN PEREZ" not in ultima_linea
    assert "recuento" in ultima_linea


# ==============================================================
# 5. PRUEBA DE CONSULTAS PREAPROBADAS Y COMPARATIVAS
# ==============================================================

def test_comparativo_facturacion_periodos():
    """Valida que la consulta comparativa genere las columnas y cálculos esperados."""
    df = comparar_facturacion_periodos(
        periodo_1_nombre="Mes_A",
        periodo_1_ini="2026-08-01",
        periodo_1_fin="2026-08-31",
        periodo_2_nombre="Mes_B",
        periodo_2_ini="2026-09-01",
        periodo_2_fin="2026-09-30"
    )

    columnas_esperadas = {
        "aseguradora",
        "Facturación Mes_A",
        "Facturación Mes_B",
        "Diferencia",
        "Variacion_%"
    }
    assert columnas_esperadas.issubset(set(df.columns))
    assert len(df) > 0
    # Comprobar que no hay NaNs en importes
    assert not df["Facturación Mes_A"].isna().any()
    assert not df["Diferencia"].isna().any()


# ==============================================================
# 6. PRUEBA DE CONSULTAS DBF (SOLO LECTURA SEGURA)
# ==============================================================

def test_consultar_dbf_directo_sin_error():
    """Valida que los módulos DBF se importen y ejecuten de forma segura sin archivo físico."""
    from src.consultas.dbf_directo import (
        consultar_dbf_admisiones_recientes,
        consultar_dbf_ordenes_recientes
    )
    df_adm = consultar_dbf_admisiones_recientes(limite=5)
    assert isinstance(df_adm, pd.DataFrame)
    assert "id_doc" in df_adm.columns

    df_ord = consultar_dbf_ordenes_recientes(limite=5)
    assert isinstance(df_ord, pd.DataFrame)
    assert "orden_id" in df_ord.columns
