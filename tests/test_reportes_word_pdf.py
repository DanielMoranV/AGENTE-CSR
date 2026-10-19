"""
Pruebas automatizadas para los generadores de Word (.docx) y PDF (.pdf) de AGENTE-CSR.
Verifica:
1. Creación exitosa de documentos en workspace/resultados/{word,pdf}/.
2. Formateo de tablas, resumen ejecutivo y conclusiones.
3. Bloqueo de path traversal en nombres de archivo.
4. Rechazo de documentos vacíos o incompletos.
5. Registro de auditoría para Word y PDF.
"""

import sys
from pathlib import Path
import pytest
import pandas as pd

_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ))

from src.reportes.word import generar_reporte_word
from src.reportes.pdf import generar_reporte_pdf
from src.reportes.validaciones import DocumentValidationError
from src.security.permissions import SecurityViolationError
from src.security.audit import AUDIT_LOG_FILE


@pytest.fixture
def datos_prueba():
    df = pd.DataFrame([
        {"aseguradora": "RIMAC SEGUROS", "facturacion": 185000.50, "variacion": 0.052},
        {"aseguradora": "PACIFICO SEGUROS", "facturacion": 142000.00, "variacion": -0.031},
        {"aseguradora": "LA POSITIVA EPS", "facturacion": 120500.80, "variacion": 0.015},
    ])
    tablas = [{
        "nombre": "Facturación por Aseguradora",
        "datos": df,
        "formatos": {"facturacion": "moneda", "variacion": "porcentaje"}
    }]
    conclusiones = [
        "Rímac Seguros consolida el primer lugar de facturación con un crecimiento de +5.2%.",
        "Pacífico Seguros registró una contracción de -3.1% debido a menor volumen en atenciones ambulatorias.",
        "Se recomienda renegociar las tarifas de procedimientos quirúrgicos con aseguradoras privadas."
    ]
    return {
        "titulo": "Informe Trimestral de Facturación Institucional",
        "subtitulo": "Periodo: Tercer Trimestre 2026 | Gerencia General",
        "resumen": "El presente informe consolida los resultados financieros y volumen de prestaciones por aseguradora. Durante el periodo evaluado se observa estabilidad en la facturación global con variaciones moderadas por convenio.",
        "tablas": tablas,
        "conclusiones": conclusiones
    }


# ==============================================================
# PRUEBAS DE GENERACIÓN WORD (.DOCX)
# ==============================================================

def test_generar_reporte_word_exitoso(datos_prueba):
    ruta = generar_reporte_word(
        titulo=datos_prueba["titulo"],
        resumen=datos_prueba["resumen"],
        tablas=datos_prueba["tablas"],
        conclusiones=datos_prueba["conclusiones"],
        nombre_archivo="test_informe_gerencia.docx",
        subtitulo=datos_prueba["subtitulo"],
        usuario="Auditor_Test"
    )
    assert ruta.exists()
    assert ruta.suffix == ".docx"
    assert ruta.stat().st_size > 1000
    assert "workspace" in str(ruta)
    assert "resultados" in str(ruta)


def test_word_bloquea_titulo_vacio(datos_prueba):
    with pytest.raises(DocumentValidationError, match="título del reporte es obligatorio"):
        generar_reporte_word(
            titulo="",
            resumen=datos_prueba["resumen"],
            tablas=datos_prueba["tablas"],
            conclusiones=datos_prueba["conclusiones"],
            nombre_archivo="error.docx"
        )


def test_word_bloquea_path_traversal(datos_prueba):
    with pytest.raises(SecurityViolationError):
        generar_reporte_word(
            titulo=datos_prueba["titulo"],
            resumen=datos_prueba["resumen"],
            tablas=datos_prueba["tablas"],
            conclusiones=datos_prueba["conclusiones"],
            nombre_archivo="../../malicious.docx"
        )


# ==============================================================
# PRUEBAS DE GENERACIÓN PDF (.PDF)
# ==============================================================

def test_generar_reporte_pdf_exitoso(datos_prueba):
    ruta = generar_reporte_pdf(
        titulo=datos_prueba["titulo"],
        resumen=datos_prueba["resumen"],
        tablas=datos_prueba["tablas"],
        conclusiones=datos_prueba["conclusiones"],
        nombre_archivo="test_informe_gerencia.pdf",
        subtitulo=datos_prueba["subtitulo"],
        usuario="Auditor_Test"
    )
    assert ruta.exists()
    assert ruta.suffix == ".pdf"
    assert ruta.stat().st_size > 1000
    assert "workspace" in str(ruta)
    assert "resultados" in str(ruta)


def test_pdf_bloquea_resumen_vacio(datos_prueba):
    with pytest.raises(DocumentValidationError, match="resumen ejecutivo es obligatorio"):
        generar_reporte_pdf(
            titulo=datos_prueba["titulo"],
            resumen="",
            tablas=datos_prueba["tablas"],
            conclusiones=datos_prueba["conclusiones"],
            nombre_archivo="error.pdf"
        )


def test_pdf_bloquea_path_traversal(datos_prueba):
    with pytest.raises(SecurityViolationError):
        generar_reporte_pdf(
            titulo=datos_prueba["titulo"],
            resumen=datos_prueba["resumen"],
            tablas=datos_prueba["tablas"],
            conclusiones=datos_prueba["conclusiones"],
            nombre_archivo="../../malicious.pdf"
        )


# ==============================================================
# AUDITORÍA DE REPORTES
# ==============================================================

def test_auditoria_registra_word_y_pdf():
    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        contenido = f.read()

    assert "GENERACION_WORD" in contenido
    assert "GENERACION_PDF" in contenido
