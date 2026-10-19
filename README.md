# AGENTE-CSR — Asistente de Análisis y Reportes para Gerencia

Sistema de inteligencia analítica y generación de reportes ejecutivos para Gerencia Médica y Administrativa en centros de salud. Diseñado bajo el principio de **Privilegio Mínimo** y **Cero Escritura** sobre fuentes transaccionales institucionales (PostgreSQL, SISCLIN y SISLAB), con un entorno de trabajo aislado para la generación controlada de informes en Excel, Word y PDF.

---

## 1. Principios de Arquitectura y Seguridad

* **Fuentes Institucionales (Estricto Solo Lectura):**
  - **PostgreSQL:** Conexión obligatoria con usuario de servicio restringido `ai_readonly`. Conexiones forzadas a nivel de sesión con `default_transaction_read_only = on` y `statement_timeout = 30000ms`. Prohibidas sentencias DDL/DML (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`).
  - **Archivos DBF / FoxPro:** Acceso binario no invasivo en modo solo lectura (`rb`) sin bloqueo de concurrencia para tablas maestras y transaccionales.
* **Espacio de Trabajo Aislado (`workspace/`):**
  - Las herramientas del agente únicamente pueden escribir dentro de `workspace/resultados/{excel,pdf,word,csv}` y `workspace/temporales/`.
  - Validación activa contra ataques de *Path Traversal* y enlaces simbólicos/junctions (`src/security/permissions.py`).
  - Sanitización automática de textos para evitar inyección de fórmulas en hojas de cálculo (*CSV/Excel Formula Injection*).
* **Control Declarativo de Capacidades (`config/capacidades.json`):**
  - Matriz que previene la ejecución de herramientas inexistentes o no autorizadas (ej. modificación de datos, envío de correos, extracción de datos personales no anonimizados).
* **Protección de Datos Personales (Normativa en Salud):**
  - Diseñado conforme a la **Ley N.º 29733** (Ley de Protección de Datos Personales), su **Reglamento (D.S. N.º 016-2024-JUS)** y estándares de reserva de la Historia Clínica (Ley N.º 26842).
  - Los reportes gerenciales presentan exclusivamente información agregada, anonimizada o consolidada por servicio, aseguradora o periodo temporal.
* **Auditoría Estructurada:**
  - Registro de eventos analíticos, solicitante, PID de proceso y UUID de sesión en `logs/audit.log` (omitiendo DNIs o datos de pacientes).

---

## 2. Estructura del Proyecto

```
AGENTE-CSR/
├── AGENTS.md                          # Directrices de rol y herramientas del Agente
├── README.md                          # Documentación principal
├── LICENSE                            # Licencia de código abierto (MIT)
├── requirements.txt                   # Dependencias de Python
├── .env.example                       # Plantilla de variables de entorno
│
├── config/
│   └── capacidades.json               # Matriz de permisos y capacidades habilitadas/bloqueadas
│
├── conocimiento/                      # Diccionarios de datos institucionales
│   ├── diccionario_sisclin.md         # Esquema de tablas y campos clínicos (SISCLIN)
│   ├── diccionario_sislab.md          # Esquema de laboratorio clínico (SISLAB)
│   └── indicadores.md                 # Definición de métricas y KPIs gerenciales
│
├── instrucciones/                     # Directivas operativas para el Agente
│   ├── agente.md                      # Tono ejecutivo y formato de respuesta
│   ├── seguridad.md                   # Políticas de solo lectura y aislamiento
│   ├── reglas_negocio.md              # Convenciones financieras y de convenios
│   └── reportes.md                    # Guía de estilo visual de documentos
│
├── scripts/                           # Scripts de provisión de infraestructura segura
│   ├── crear_usuario_postgres.sql     # Creación del rol restringido 'ai_readonly'
│   └── aplicar_permisos_ntfs.ps1      # Configuración de permisos NTFS en Windows
│
├── src/                               # Código fuente certificado
│   ├── database/                      # Conectores seguros a bases de datos
│   │   └── connection.py              # Engine PostgreSQL de solo lectura y timeout
│   ├── dbf_reader/                    # Lectores optimizados para archivos DBF / CDX
│   │   ├── foxpro_reader.py           # Parser binario robusto de solo lectura
│   │   └── cdx_reader.py              # Lector de índices CDX (solo lectura)
│   ├── security/                      # Controles de seguridad y sandboxing
│   │   ├── permissions.py             # Validación de rutas anti-traversal y sanitización
│   │   ├── capacidades.py             # Validador de capacidades frente a capacidades.json
│   │   └── audit.py                   # Logger de auditoría estructurado
│   ├── consultas/                     # Catálogo de consultas preaprobadas
│   │   ├── facturacion.py             # Comparativas de ingresos por aseguradora
│   │   ├── admisiones.py              # Demanda y atenciones por especialidad
│   │   ├── laboratorio.py             # Catálogo de pruebas frecuentes
│   │   ├── farmacia.py                # Adquisición de insumos y compras
│   │   └── dbf_directo.py             # Consultas en caliente a tablas DBF (sc0011, sc0020)
│   └── reportes/                      # Motores de exportación ejecutiva
│       ├── estilos.py                 # Paleta corporativa, tipografía y metadatos
│       ├── validaciones.py            # Validación de datos antes de generar entregables
│       ├── excel.py                   # Generador de libros .xlsx con totales y gráficos
│       ├── word.py                    # Generador de informes ejecutivos .docx
│       └── pdf.py                     # Generador de documentos foliados .pdf
│
├── tests/                             # Suite de pruebas automatizadas
│   ├── test_seguridad.py              # Pruebas de Path Traversal, inyecciones y permisos
│   ├── test_matriz_evaluacion.py      # Validación de matriz de resiliencia y controles
│   └── test_reportes_word_pdf.py      # Pruebas de exportación Word y PDF
│
├── test_reporte_gerencia.py           # Script piloto: Reporte Excel con comparativa y gráfico
├── test_informe_trimestral_gerencia.py # Script piloto: Reporte trimestral multiformato (Excel+Word+PDF)
│
├── workspace/                         # Área exclusiva de lectura/escritura del Agente
│   ├── temporales/                    # Archivos intermedios de cálculo
│   └── resultados/                    # Entregables generados (excel, word, pdf, csv)
│
└── logs/                              # Registro local de auditoría
    └── audit.log
```

---

## 3. Instalación y Puesta en Marcha

### Requisitos Previos
* Python 3.10 o superior.
* Servidor PostgreSQL con la base de datos institucional y el usuario `ai_readonly` configurado (ver `scripts/crear_usuario_postgres.sql`).
* Acceso de red (SMB/NFS) a las carpetas DBF de SISCLIN/SISLAB (opcional para pruebas con datos sintéticos).

### Pasos de Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/DanielMoranV/AGENTE-CSR.git
   cd AGENTE-CSR
   ```

2. **Crear y activar el entorno virtual:**
   * **En Linux / macOS / WSL:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   * **En Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar el entorno:**
   Copiar la plantilla de configuración y editar las credenciales de conexión:
   ```bash
   cp .env.example .env
   ```

---

## 4. Ejecución de Pruebas y Validaciones

### Pruebas Automatizadas (Pytest)
El proyecto cuenta con una suite completa de pruebas unitarias y de integración que validan los controles de seguridad, aislamiento de rutas, consultas preaprobadas y generación de documentos:

```bash
pytest
```
*(24 pruebas aprobadas: seguridad, matriz de evaluación, generadores Word/PDF y módulos DBF).*

### Scripts de Demostración

* **Reporte de Facturación en Excel con Gráfico Integrado:**
  ```bash
  python test_reporte_gerencia.py
  ```
  Genera un libro en `workspace/resultados/excel/` con análisis comparativo entre periodos, formato de moneda, variación porcentual y gráfico de barras.

* **Flujo Gerencial Trimestral Multiformato (Excel + Word + PDF):**
  ```bash
  python test_informe_trimestral_gerencia.py
  ```
  Ejecuta la consolidación de 3 meses, generando simultáneamente el libro Excel, un informe ejecutivo en `.docx` y un documento formateado en `.pdf`.

---

## 5. Licencia

Este proyecto se distribuye bajo los términos de la Licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más información.
