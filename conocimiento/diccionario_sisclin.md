# Diccionario de Datos: SISCLIN (Clínica y Facturación)

Este documento resume las principales entidades del sistema clínico y de facturación SISCLIN, su fuente DBF y su representación en PostgreSQL (esquema `sisclin`).

---

## 1. Tablas Maestras

| Tabla PostgreSQL | Archivo DBF | Clave Primaria / Upsert | Descripción |
|---|---|---|---|
| `sisclin.aseguradoras` | `sc0002.dbf` | `id_cia` | Compañías de seguros, EPS y convenios institucionales. |
| `sisclin.empresas` | `SC0003.DBF` | `id_emp` | Empresas contratantes asociadas a aseguradoras. |
| `sisclin.pacientes` | `sc0004.DBF` | `id_pac` | Maestro de pacientes (DNI, nombres, fecha nacimiento, sexo, teléfono). |
| `sisclin.servicios_medicos` | `sc0006.dbf` | `codigo_servicio_medico` | Especialidades y servicios médicos clínicos. |
| `sisclin.tarifario_general` | `SC0008.DBF` | `codigo_segus` | Catálogo de prestaciones médicas, tarifario SEGUS y precios base. |
| `sisclin.diagnosticos_cie` | `sc0007.dbf` | `codigo_cie` | Catálogo internacional de enfermedades CIE-10. |
| `sisclin.productos_farmacia`| `sc00f1.DBF` | `codigo_producto` | Medicamentos e insumos de farmacia. |
| `sisclin.proveedores_farmacia`| `SC00F3.DBF` | `codigo_proveedor` | Proveedores de farmacia e insumos. |

---

## 2. Tablas Transaccionales Clínicas

### `sisclin.atenciones` (`sc0011.DBF`)
* **Propósito:** Registro central de admisiones médicas (consultas, emergencias, hospitalizaciones).
* **Campos clave:**
  - `id_doc` / `numero_documento`: Número correlativo de la admisión.
  - `id_pac`: Identificador del paciente.
  - `fecha_ingreso` / `hora_ingreso`: Momento de admisión.
  - `fecha_alta`: Momento de cierre o alta médica.
  - `tipo_atencion`: Código de tipo (Ambulatorio, Emergencia, Hospitalización).
  - `id_cia`: Aseguradora asignada a la cuenta.
  - `codigo_medico`: Médico tratante o de guardia.
  - `estado`: Estado de la cuenta (abierta, liquidada, cerrada, anulada).

### `sisclin.turnos_atenciones` (`sc1001.DBF`)
* **Propósito:** Citas médicas programadas y turnos de atención ambulatoria.
* **Campos clave:** `id_turno`, `id_pac`, `fecha_turno`, `codigo_medico`, `codigo_servicio`.

### `sisclin.historias_digitales` (`Sh0500f.DBF`) y Auxiliares
* `sh0500f`: Cabecera de historia clínica digital (`id_hc`, `id_doc`, `fecha`, `anamnesis`).
* `sh0500d`: Signos vitales (`presion_arterial`, `temperatura`, `frecuencia_cardiaca`, `saturacion_oxigeno`).
* `sh0500e`: Diagnósticos de la atención (`codigo_cie`, `tipo_diagnostico`: presuntivo/definitivo).
* `sh0500h`: Prescripciones médicas farmacológicas.

---

## 3. Tablas de Facturación y Finanzas

### `sisclin.comprobantes` (`sc0017.DBF`)
* **Propósito:** Facturación agrupada y comprobantes emitidos.
* **Campos clave:**
  - `numero_factura`: Serie y número de factura/boleta.
  - `id_doc`: Número de admisión vinculada.
  - `id_cia`: Aseguradora a la que se factura.
  - `fecha_emision`: Fecha fiscal de emisión.
  - `total_factura`: Monto total bruto del comprobante.
  - `igv`: Impuesto general a las ventas.
  - `estado`: Emitida, anulada, cobrada.

### `sisclin.comprobantes_tickets` (`sc0030.DBF`)
* **Propósito:** Comprobantes individuales emitidos por caja (tickets, boletas particulares, copagos).
* **Campos clave:** `serie_comprobante`, `numero_comprobante`, `fecha_ticket`, `total_ticket`, `copago`.

### `sisclin.notas_credito` (`sc0019.DBF`)
* **Propósito:** Anulaciones o rebajas sobre facturas emitidas.
* **Campos clave:** `numero_nota_credito`, `numero_factura_referencia`, `fecha_emision`, `monto_total`.
* **Nota importante para cálculos:** Siempre debe restarse de la facturación bruta.

### `sisclin.detalle_servicios` (`sc0012.DBF`)
* **Propósito:** Desglose línea por línea de las prestaciones cargadas a una cuenta médica.
* **Campos clave:** `id_doc`, `codigo_segus`, `cantidad`, `precio_unitario`, `subtotal`.

---

## 4. Farmacia

* `sisclin.guias_farmacia` (`sc00f7.DBF`): Cabecera de despacho de medicamentos.
* `sisclin.detalle_guias_farmacia` (`SC00F8.DBF`): Items despachados (`codigo_producto`, `cantidad`, `precio`).
* `sisclin.ordenes_compra_farmacia` (`SC0205A.DBF`): Compras a proveedores.
