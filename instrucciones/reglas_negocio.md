# Instrucciones: Reglas de Negocio Hospitalario

## 1. Módulos y Flujos de la Clínica

### A. Admisiones y Atenciones (`sisclin.atenciones` / `sc0011.DBF`)
- Una **Admisión** (`numero_documento` o `id_doc`) representa el ingreso o cita de un paciente.
- Tipos de Atención comunes:
  - Ambulatoria / Consulta externa.
  - Emergencia.
  - Hospitalización.
  - Procedimientos / Cirugía (`SC0011QX`).
- El estado de la atención define si está activa, de alta o anulada.

### B. Facturación y Cobranza (`sisclin.comprobantes` / `sc0017`, `sc0030`, `sc0019`)
- **Facturas / Boletas:** Comprobantes emitidos a pacientes particulares o empresas/aseguradoras.
- **Notas de Crédito (`sc0019`):** Deben descontarse del importe bruto facturado para obtener la **Facturación Neta**.
- **Aseguradoras / Convenios (`sc0002`):**
  - Convenios con aseguradoras principales (Rímac, Pacífico, La Positiva, Sanitas, Mapfre, etc.).
  - Copagos y deducibles a cargo del paciente vs. Cobertura a cargo de la aseguradora.

### C. Laboratorio Clínico (`sislab.ordenes` / `SC0020`, `SC0021`)
- Las órdenes de laboratorio tienen su propio correlativo (`orden_id`).
- Se vinculan a las atenciones clínicas mediante el número de admisión (`admision_sisclin` o a través de `guias_laboratorio`).
- Un paciente puede tener múltiples órdenes en una misma hospitalización.

## 2. Convenciones Financieras
- **Moneda:** Salvo indicación expresa, los importes se expresan en Soles (`PEN` / `S/`).
- **Facturación Neta:** `Facturación Bruta - Notas de Crédito - Descuentos`.
- **Periodos de Comparación:** Utilizar mes calendario completo o rangos simétricos de días para evitar sesgos por número de días hábiles.
