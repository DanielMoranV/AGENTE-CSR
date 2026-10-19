"""
Script de prueba piloto para AGENTE-CSR.
Simula la solicitud de Gerencia:
"Compara la facturación de agosto y septiembre de 2026 por aseguradora y genera un reporte Excel con gráfico."
"""

import sys
from pathlib import Path

# Añadir raíz al sys.path para importaciones
_RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(_RAIZ))

from src.consultas.facturacion import comparar_facturacion_periodos
from src.reportes.excel import generar_reporte_excel


def main():
    print("==================================================")
    print("AGENTE-CSR — Prueba de Generación de Reporte")
    print("==================================================")
    
    # 1. Obtener datos analíticos comparativos
    print("\n1. Obteniendo datos comparativos de facturación...")
    df = comparar_facturacion_periodos(
        periodo_1_nombre="Agosto 2026",
        periodo_1_ini="2026-08-01",
        periodo_1_fin="2026-08-31",
        periodo_2_nombre="Septiembre 2026",
        periodo_2_ini="2026-09-01",
        periodo_2_fin="2026-09-30"
    )
    
    print("\nResumen de datos procesados:")
    print(df.to_string(index=False))
    
    # 2. Generar Excel ejecutivo con estilos, totales y gráfico
    print("\n2. Generando reporte Excel en workspace/resultados/excel/...")
    
    col1 = "Facturación Agosto 2026"
    col2 = "Facturación Septiembre 2026"
    
    ruta_generada = generar_reporte_excel(
        df=df,
        nombre_archivo="comparativo_facturacion_agosto_septiembre_2026.xlsx",
        titulo="Clínica Institucional — Reporte Gerencial de Facturación",
        subtitulo="Comparativo de Ingresos por Aseguradora: Agosto 2026 vs Septiembre 2026",
        formatos_columnas={
            col1: "moneda",
            col2: "moneda",
            "Diferencia": "moneda",
            "Variacion_%": "porcentaje"
        },
        incluir_totales=True,
        columnas_totales=[col1, col2, "Diferencia"],
        crear_grafico=True,
        grafico_config={
            "titulo": "Facturación por Aseguradora (Agosto vs Septiembre)",
            "categoria": "aseguradora",
            "valores": [col1, col2]
        },
        usuario="Gerencia General"
    )
    
    print(f"\n[OK] Reporte generado exitosamente:")
    print(f"  Ruta: {ruta_generada}")
    print(f"  Tamaño: {ruta_generada.stat().st_size:,} bytes")
    
    # 3. Comprobar log de auditoría
    audit_file = _RAIZ / "logs" / "audit.log"
    if not audit_file.exists():
        audit_file = Path("C:/AGENTE-CSR/logs/audit.log")
    if audit_file.exists():
        print(f"\n[OK] Auditoría registrada en: {audit_file}")
        with open(audit_file, "r", encoding="utf-8") as f:
            lineas = f.readlines()
            print(f"  Última entrada de auditoría: {lineas[-1].strip()}")


if __name__ == "__main__":
    main()
