# Instrucciones: Estándar y Guía de Estilo de Reportes

## 1. Diseño Ejecutivo en Excel (.xlsx)

Todo libro generado por el agente debe cumplir con los siguientes estándares visuales y estructurales:

1. **Tipografía:** Segoe UI, Aptos o Calibri en toda la hoja.
2. **Paleta de Colores Corporativa:**
   - Cabeceras principales: Azul Institucional `#1F4E78` o Azul Marino `#0F2537` con texto en blanco y negrita.
   - Subtotales y secciones: Gris azulado `#D9E1F2`.
   - Fila de Total General: Fondo `#203764` o `#305496` con texto blanco, negrita y doble línea inferior.
   - Variaciones positivas: Texto verde `#276A3C` o fondo verde suave `#E2EFDA`.
   - Variaciones negativas: Texto rojo `#9C0006` o fondo rojo suave `#FFC7CE`.
3. **Formato de Celdas:**
   - Monedas: `S/ #,##0.00`
   - Cantidades / Contadores: `#,##0`
   - Porcentajes: `0.0%` o `+0.0%;-0.0%;0.0%`
   - Fechas: `YYYY-MM-DD`
4. **Disposición:**
   - Fila 1: Título del Reporte (Negrita, tamaño 14-16).
   - Fila 2: Subtítulo con rango de fechas analizado y fecha de corte de emisión.
   - Fila 3: Vacía (separador).
   - Fila 4: Cabecera de la tabla de datos.
   - Ajuste automático de ancho de columnas (`auto-fit`) con un margen mínimo para evitar celdas con `###`.
   - Congelar paneles (`freeze panes`) en la cabecera para facilitar la navegación en tablas largas.
5. **Gráficos Integrados:**
   - Si la solicitud pide gráficos o comparativa temporal/aseguradora, insertar el gráfico de `openpyxl` al costado o debajo de la tabla principal.

## 2. Reportes PDF / Word
- Usar orientación horizontal (Landscape) para tablas financieras de muchas columnas.
- Incluir número de página y fecha de emisión en el pie de página.
