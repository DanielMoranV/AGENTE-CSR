"""
Generador de Reportes Ejecutivos en PDF para AGENTE-CSR.
Utiliza ReportLab (Platypus) con paleta institucional, foliado dinámico ('Página X de Y'),
caja de resumen ejecutivo, tablas de alta fidelidad y auditoría de seguridad.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Spacer,
    KeepTogether,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from src.reportes.estilos import (
    HEX_NAVY_PRIMARY,
    HEX_BLUE_SECONDARY,
    HEX_GRAY_BG,
    HEX_DARK_TEXT,
    HEX_BORDER,
    NOMBRE_INSTITUCION,
    CONFIDENCIALIDAD_TEXTO
)
from src.reportes.validaciones import validar_contenido_documento, validar_destino_reporte
from src.security.audit import registrar_evento_auditoria


def _hex(color_str: str) -> colors.HexColor:
    """Convierte cualquier cadena hexadecimal en HexColor válido con prefijo #."""
    return colors.HexColor(f"#{str(color_str).lstrip('#')}")


class CanvasNumerado(canvas.Canvas):
    """
    Canvas personalizado de ReportLab que realiza dos pasadas para calcular
    el total de páginas y estampar 'Página X de Y' junto con membrete institucional.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_paginas = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.dibujar_encabezado_pie(num_paginas)
            super().showPage()
        super().save()

    def dibujar_encabezado_pie(self, total_paginas: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(_hex("#595959"))

        # Encabezado (Páginas > 0)
        self.drawString(54, 755, f"{NOMBRE_INSTITUCION} — Dirección Médica y Gerencia General")
        self.setStrokeColor(_hex(HEX_BORDER))
        self.setLineWidth(0.5)
        self.line(54, 750, 558, 750)

        # Pie de página
        self.line(54, 45, 558, 45)
        texto_pie = f"{CONFIDENCIALIDAD_TEXTO}"
        self.drawString(54, 32, texto_pie)
        
        pag_texto = f"Pág. {self._pageNumber} de {total_paginas}"
        self.drawRightString(558, 32, pag_texto)
        self.restoreState()


def generar_reporte_pdf(
    titulo: str,
    resumen: str,
    tablas: Optional[List[Dict[str, Any]]],
    conclusiones: Optional[List[str]],
    nombre_archivo: str,
    subtitulo: str = "",
    usuario: Optional[str] = None
) -> Path:
    """
    Genera un informe institucional formal en formato PDF listo para Gerencia.
    """
    # 1. Validación de seguridad de rutas y contenido
    validar_contenido_documento(titulo, resumen, tablas, conclusiones)
    ruta_destino = validar_destino_reporte(nombre_archivo, "pdf")

    # 2. Configuración del documento (márgenes de 54 pt = 0.75 pulgadas)
    doc = SimpleDocTemplate(
        str(ruta_destino),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Estilos tipográficos
    style_titulo = ParagraphStyle(
        'DocTitulo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=_hex(HEX_NAVY_PRIMARY),
        spaceAfter=4
    )
    style_subtitulo = ParagraphStyle(
        'DocSubtitulo',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        textColor=_hex("#595959"),
        spaceAfter=14
    )
    style_h1 = ParagraphStyle(
        'DocH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=_hex(HEX_BLUE_SECONDARY),
        spaceBefore=10,
        spaceAfter=6
    )
    style_resumen = ParagraphStyle(
        'DocResumen',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=_hex(HEX_DARK_TEXT)
    )
    style_tabla_header = ParagraphStyle(
        'DocTH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1, # Centro
        textColor=colors.white
    )
    style_tabla_celda = ParagraphStyle(
        'DocTD',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=_hex(HEX_DARK_TEXT)
    )
    style_tabla_celda_der = ParagraphStyle(
        'DocTDR',
        parent=style_tabla_celda,
        alignment=2 # Derecha
    )
    style_bullet = ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=_hex(HEX_DARK_TEXT),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    story = []

    # 3. Título y Subtítulo
    story.append(Paragraph(titulo, style_titulo))
    sub_texto = subtitulo or f"Fecha de emisión: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    story.append(Paragraph(sub_texto, style_subtitulo))

    # 4. Resumen Ejecutivo (en caja destacada)
    story.append(Paragraph("1. Resumen Ejecutivo", style_h1))
    
    p_resumen = Paragraph(resumen, style_resumen)
    t_resumen = Table([[p_resumen]], colWidths=[504])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), _hex(HEX_GRAY_BG)),
        ('BOX', (0, 0), (-1, -1), 1, _hex(HEX_BLUE_SECONDARY)),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 12))

    # 5. Tablas de Datos
    if tablas:
        story.append(Paragraph("2. Cuadros Analíticos y Datos Detallados", style_h1))

        for idx, item in enumerate(tablas):
            nombre_tabla = item.get("nombre", f"Cuadro {idx+1}")
            df = item.get("datos")
            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                continue

            story.append(Paragraph(f"<b>Cuadro:</b> {nombre_tabla}", style_resumen))
            story.append(Spacer(1, 4))

            cols = list(df.columns)
            formatos = item.get("formatos", {})

            # Matriz de celdas
            data_matriz = []
            # Fila de cabecera
            hdr_fila = [Paragraph(str(c).replace("_", " ").title(), style_tabla_header) for c in cols]
            data_matriz.append(hdr_fila)

            # Filas de datos
            for _, row in df.iterrows():
                fila = []
                for c in cols:
                    val = row[c]
                    fmt = formatos.get(c, "")
                    if fmt == "moneda" and isinstance(val, (int, float)):
                        t_val = f"S/ {val:,.2f}"
                        st = style_tabla_celda_der
                    elif fmt == "porcentaje" and isinstance(val, (int, float)):
                        t_val = f"{val * 100:.1f}%"
                        st = style_tabla_celda_der
                    elif isinstance(val, (int, float)):
                        t_val = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
                        st = style_tabla_celda_der
                    else:
                        t_val = str(val or "")
                        st = style_tabla_celda
                    fila.append(Paragraph(t_val, st))
                data_matriz.append(fila)

            # Ancho de columnas equitativo
            ancho_col = 504 / len(cols)
            t_data = Table(data_matriz, colWidths=[ancho_col] * len(cols), repeatRows=1)
            
            # Estilos de tabla corporativos
            t_style = [
                ('BACKGROUND', (0, 0), (-1, 0), _hex(HEX_NAVY_PRIMARY)),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, _hex(HEX_BORDER)),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
            # Alternar color de fondo en filas
            for r in range(1, len(data_matriz)):
                bg = _hex(HEX_GRAY_BG) if (r % 2 == 0) else colors.white
                t_style.append(('BACKGROUND', (0, r), (-1, r), bg))

            t_data.setStyle(TableStyle(t_style))
            story.append(t_data)
            story.append(Spacer(1, 10))

    # 6. Conclusiones y Recomendaciones
    if conclusiones:
        story.append(Paragraph("3. Conclusiones y Recomendaciones", style_h1))
        for conc in conclusiones:
            bullet_p = Paragraph(f"• <b>{conc}</b>" if ":" in conc else f"• {conc}", style_bullet)
            story.append(bullet_p)

    # 7. Construir PDF con foliado dinámico
    doc.build(story, canvasmaker=CanvasNumerado)

    # Auditoría
    registrar_evento_auditoria(
        accion="GENERACION_PDF",
        modulo="reportes.pdf",
        operacion="generar_reporte_pdf",
        detalles={
            "archivo": str(ruta_destino),
            "titulo": titulo[:80],
            "tablas_incluidas": len(tablas) if tablas else 0,
            "conclusiones_count": len(conclusiones) if conclusiones else 0
        },
        usuario=usuario,
        estado="EXITO"
    )

    return ruta_destino
