# Instrucciones de Seguridad y Políticas de Aislamiento

## 1. Política de Cero Escritura en Datos Transaccionales
- Toda conexión o herramienta que interactúe con PostgreSQL debe utilizar un usuario con permisos exclusivos de `SELECT`.
- Los módulos de lectura DBF deben abrir los archivos exclusivamente con el modo de lectura binaria: `open(path, 'rb')`. No se permiten llamadas a `open(path, 'wb')`, `open(path, 'rb+')` ni métodos de modificación de DBF sobre carpetas compartidas.

## 2. Aislamiento de Entorno de Archivos
- **Carpeta permitida de salida:** Todo archivo producido (Excel, CSV, PDF, Word) debe tener una ruta canónica que comience con:
  `C:\AGENTE-CSR\workspace\`
- Cualquier intento de escribir en `C:\Windows`, `C:\Program Files`, en la raíz `C:\` o en las carpetas de red compartidas de la clínica provocará una excepción de seguridad y la terminación inmediata del proceso.

## 3. Sanitización de Exportaciones (CSV / Excel Injection)
- Los campos de texto libre (nombres de pacientes, diagnósticos, observaciones) no deben comenzar con caracteres de fórmula de Excel (`=`, `+`, `-`, `@`, `\t`, `\r`) en archivos generados.
- El módulo `src/security/permissions.py` debe sanear estos caracteres anteponiendo una comilla simple (`'`) si están presentes.

## 4. Auditoría
- Cada ejecución de reporte debe quedar registrada en `C:\AGENTE-CSR\logs\audit.log` indicando:
  - Timestamp.
  - Usuario / Solicitante.
  - Parámetros de la consulta (rango de fechas, tablas involucradas).
  - Archivo generado y cantidad de registros procesados.
