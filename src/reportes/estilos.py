"""
Estilos y Guía Visual Corporativa compartida para AGENTE-CSR.
Unifica colores, fuentes y directrices para Excel, Word y PDF.
"""

import os
from typing import Dict, Any

# ==============================================================
# PALETA DE COLORES CORPORATIVOS (Hex y Tuplas RGB)
# ==============================================================
HEX_NAVY_DARK = "0F2537"       # Azul muy oscuro institucional
HEX_NAVY_PRIMARY = "1F4E78"    # Azul institucional primario (Encabezados)
HEX_BLUE_SECONDARY = "2E75B6"  # Azul de acento (Subtítulos, bordes destacados)
HEX_BLUE_LIGHT = "D9E1F2"      # Azul claro de fondo (Totales, destacados)
HEX_GRAY_BG = "F2F4F8"         # Fondo suave para filas alternas (Zebra)
HEX_GRAY_SUBTITLE = "595959"   # Gris para texto secundario
HEX_DARK_TEXT = "262626"       # Texto principal (casi negro)
HEX_BORDER = "D3D3D3"          # Bordes suaves de tablas
HEX_WHITE = "FFFFFF"

# Tuplas RGB (0-255) para docx y reportlab
RGB_NAVY_PRIMARY = (31, 78, 120)
RGB_BLUE_SECONDARY = (46, 117, 182)
RGB_BLUE_LIGHT = (217, 225, 242)
RGB_GRAY_BG = (242, 244, 248)
RGB_DARK_TEXT = (38, 38, 38)
RGB_WHITE = (255, 255, 255)
RGB_BORDER = (211, 211, 211)

# ==============================================================
# NORMAS TIPOGRÁFICAS
# ==============================================================
FONT_PRIMARY_DOCX = "Segoe UI"
FONT_FALLBACK_DOCX = "Calibri"
FONT_PRIMARY_PDF = "Helvetica"
FONT_BOLD_PDF = "Helvetica-Bold"
FONT_OBLIQUE_PDF = "Helvetica-Oblique"

# ==============================================================
# METADATOS INSTITUCIONALES
# ==============================================================
NOMBRE_INSTITUCION = os.environ.get("NOMBRE_INSTITUCION", "Clínica Institucional")
SISTEMA_ORIGEN = "AGENTE-CSR — Inteligencia de Negocios y Operaciones"
CONFIDENCIALIDAD_TEXTO = "DOCUMENTO DE USO INTERNO Y EXCLUSIVO PARA GERENCIA — CONFIDENCIAL"
