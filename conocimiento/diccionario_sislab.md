# Diccionario de Datos: SISLAB (Laboratorio Clínico)

Este documento resume las entidades del sistema legacy independiente de Laboratorio Clínico SISLAB, su fuente DBF y su representación en PostgreSQL (esquema `sislab`).

---

## 1. Tablas Maestras

| Tabla PostgreSQL | Archivo DBF | Clave Primaria / Upsert | Descripción |
|---|---|---|---|
| `sislab.catalogo_examenes` | `sc0007.DBF` | `examen_id` | Catálogo de pruebas y perfiles de laboratorio (Hemograma, Glucosa, etc.). |
| `sislab.pacientes` | `sc0004.dbf` | `paciente_id` | Maestro de pacientes registrados en el sistema de laboratorio. |
| `sislab.companias` | `sc0002.DBF` | `compania_id` | Compañías de seguros registradas en laboratorio. |
| `sislab.aseguradoras` | `SC0003.DBF` | `empresa_id` | Empresas contratantes en laboratorio. |
| `sislab.rangos_parametros`| `sc0015.dbf` | `parametro_id` + grupo | Valores de referencia, rangos por sexo y edad, unidades de medida. |

---

## 2. Tablas Transaccionales de Laboratorio

### `sislab.ordenes` (`SC0020.DBF`)
* **Propósito:** Registro central de órdenes de análisis de laboratorio.
* **Campos clave:**
  - `orden_id`: Número único de la orden de laboratorio (ej: `2026-001234` o correlativo numérico).
  - `fecha_orden` / `hora_orden`: Fecha de recepción de la muestra / generación de la orden.
  - `paciente_id`: Paciente asociado.
  - `origen`: Procedencia del paciente (Emergencia, Hospitalización, Ambulatorio, Externo).
  - `medico_solicitante`: Nombre o código del médico prescriptor.
  - `admision_sisclin`: Vínculo directo opcional con la admisión de `sisclin.atenciones`.
  - `estado`: Estado de la orden (Pendiente, Procesada, Validada, Entregada).

### `sislab.ordenes_detalle` (`SC0021.DBF`)
* **Propósito:** Pruebas específicas y resultados asociados a una orden.
* **Campos clave:**
  - `orden_id`: Orden a la que pertenece el detalle.
  - `correlativo`: Línea de la orden.
  - `examen_id`: Código de la prueba (relacionado con `catalogo_examenes`).
  - `parametro_id`: Parámetro individual (ej: Leucocitos, Plaquetas dentro de Hemograma).
  - `resultado`: Valor textual o numérico obtenido.
  - `valor_referencia`: Rango normal esperado.
  - `es_anormal`: Indicador booleano o flag de resultado fuera de rango.
  - `fecha_resultado`: Fecha y hora de validación bioquímica.

---

## 3. Vínculo entre SISCLIN y SISLAB
- **Vía Guías de Laboratorio:** `sisclin.guias_laboratorio.numero_orden_sislab` ↔ `sislab.ordenes.orden_id`.
- **Vía Admisión Directa:** `sislab.ordenes.admision_sisclin` ↔ `sisclin.atenciones.numero_documento`.
