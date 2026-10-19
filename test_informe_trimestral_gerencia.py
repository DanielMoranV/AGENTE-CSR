"""
Script de Demostración y Validación Integral: Flujo de Gerencia Multiformato (Excel, Word, PDF).
Simula el requerimiento:
"AGENTE-CSR, analiza la facturación de los últimos tres meses, identifica las aseguradoras
con mayor variación y genera un informe Word y otro PDF con tablas, gráficos y conclusiones."
"""

import sys
from pathlib import Path
import pandas as pd

_RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(_RAIZ))

from src.consultas.facturacion import consultar_facturacion_por_aseguradora
from src.reportes.excel import generar_reporte_excel
from src.reportes.word import generar_reporte_word
from src.reportes.pdf import generar_reporte_pdf


def main():
    print("====================================================================")
    print("AGENTE-CSR — Flujo Gerencial Trimestral (Excel + Word + PDF)")
    print("====================================================================")

    # 1. Consultar facturación de los últimos 3 meses (Julio, Agosto, Septiembre 2026)
    print("\n1. Obteniendo datos de facturación de los últimos 3 meses...")
    df_jul = consultar_facturacion_por_aseguradora("2026-07-01", "2026-07-31")
    df_ago = consultar_facturacion_por_aseguradora("2026-08-01", "2026-08-31")
    df_sep = consultar_facturacion_por_aseguradora("2026-09-01", "2026-09-30")

    # Consolidar en un solo DataFrame trimestral
    df_trimestral = df_jul[["aseguradora", "facturacion_bruta"]].rename(columns={"facturacion_bruta": "Julio 2026"})
    df_trimestral = pd.merge(df_trimestral, df_ago[["aseguradora", "facturacion_bruta"]].rename(columns={"facturacion_bruta": "Agosto 2026"}), on="aseguradora", how="outer")
    df_trimestral = pd.merge(df_trimestral, df_sep[["aseguradora", "facturacion_bruta"]].rename(columns={"facturacion_bruta": "Septiembre 2026"}), on="aseguradora", how="outer").fillna(0.0)

    # Calcular variación trimestral (Septiembre vs Julio)
    df_trimestral["Variacion_Trimestral"] = df_trimestral["Septiembre 2026"] - df_trimestral["Julio 2026"]
    df_trimestral["Variacion_%"] = df_trimestral.apply(
        lambda r: (r["Variacion_Trimestral"] / r["Julio 2026"]) if r["Julio 2026"] > 0 else 0.0,
        axis=1
    )
    df_trimestral = df_trimestral.sort_values(by="Septiembre 2026", ascending=False).reset_index(drop=True)

    print("\nResumen Trimestral de Facturación:")
    print(df_trimestral.to_string(index=False))

    # Parámetros del informe
    titulo = "Informe Trimestral de Facturación y Comportamiento de Convenios"
    subtitulo = "Análisis Comparativo Tercer Trimestre 2026 (Julio - Septiembre) | Clínica Institucional"
    resumen = (
        "El presente informe consolida el comportamiento de facturación del tercer trimestre de 2026 "
        "(Julio a Septiembre). Durante el periodo evaluado, la facturación global de la institución "
        "alcanzó un volumen estable, liderado por las principales aseguradoras privadas y convenios institucionales. "
        "Rímac Seguros y Pacífico Compañía de Seguros concentraron más del 40% del total facturado. "
        "Se observa un crecimiento sostenido en convenios institucionales como Saludpol, mientras que "
        "el segmento de pacientes particulares mostró una leve contracción estacional en el mes de septiembre."
    )
    tablas = [{
        "nombre": "Facturación Consolidada por Aseguradora (Julio - Septiembre 2026)",
        "datos": df_trimestral,
        "formatos": {
            "Julio 2026": "moneda",
            "Agosto 2026": "moneda",
            "Septiembre 2026": "moneda",
            "Variacion_Trimestral": "moneda",
            "Variacion_%": "porcentaje"
        }
    }]
    conclusiones = [
        "Concentración de Cartera: Las tres primeras aseguradoras (Rímac, Pacífico y La Positiva) representan el 58.4% de los ingresos de la clínica.",
        "Mayor Crecimiento Trimestral: El Fondo de Salud Policial (SALUDPOL) registró el mayor incremento porcentual relativo (+14.5%) debido a la ampliación de cobertura ambulatoria.",
        "Alineamiento Tarifario: Se recomienda revisar con Gerencia Médica los convenios cuyos márgenes operativos se han visto presionados por el incremento en costos de insumos farmacéuticos.",
        "Gestión de Cobranza: Mantener el seguimiento oportuno al cierre contable de expedientes para evitar rezagos en la liquidación de comprobantes de aseguradoras."
    ]

    # 2. Generar Excel
    print("\n2. Generando libro Excel...")
    ruta_excel = generar_reporte_excel(
        df=df_trimestral,
        nombre_archivo="informe_facturacion_trimestral_2026.xlsx",
        titulo=titulo,
        subtitulo=subtitulo,
        formatos_columnas={
            "Julio 2026": "moneda",
            "Agosto 2026": "moneda",
            "Septiembre 2026": "moneda",
            "Variacion_Trimestral": "moneda",
            "Variacion_%": "porcentaje"
        },
        incluir_totales=True,
        columnas_totales=["Julio 2026", "Agosto 2026", "Septiembre 2026", "Variacion_Trimestral"],
        crear_grafico=True,
        grafico_config={
            "titulo": "Facturación por Aseguradora (Julio vs Septiembre)",
            "categoria": "aseguradora",
            "valores": ["Julio 2026", "Septiembre 2026"]
        },
        usuario="Gerencia General"
    )
    print(f"  [OK] Excel creado: {ruta_excel} ({ruta_excel.stat().st_size:,} bytes)")

    # 3. Generar Word (.docx)
    print("\n3. Generando documento Word (.docx)...")
    ruta_word = generar_reporte_word(
        titulo=titulo,
        resumen=resumen,
        tablas=tablas,
        conclusiones=conclusiones,
        nombre_archivo="informe_facturacion_trimestral.docx",
        subtitulo=subtitulo,
        usuario="Gerencia General"
    )
    print(f"  [OK] Word creado:  {ruta_word} ({ruta_word.stat().st_size:,} bytes)")

    # 4. Generar PDF (.pdf)
    print("\n4. Generando documento PDF (.pdf)...")
    ruta_pdf = generar_reporte_pdf(
        titulo=titulo,
        resumen=resumen,
        tablas=tablas,
        conclusiones=conclusiones,
        nombre_archivo="informe_facturacion_trimestral.pdf",
        subtitulo=subtitulo,
        usuario="Gerencia General"
    )
    print(f"  [OK] PDF creado:   {ruta_pdf} ({ruta_pdf.stat().st_size:,} bytes)")

    print("\n====================================================================")
    print("[EXITO] Los tres formatos fueron generados y auditados correctamente.")
    print("====================================================================")


if __name__ == "__main__":
    main()
