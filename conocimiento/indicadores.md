# Indicadores Clave de Desempeño (KPIs) Hospitalarios

Este documento define la metodología y fórmulas para el cálculo de indicadores analíticos solicitados por Gerencia.

---

## 1. Indicadores Financieros y Facturación

### A. Facturación Neta
$$\text{Facturación Neta} = \sum (\text{Total Factura} + \text{Total Boletas/Tickets}) - \sum (\text{Notas de Crédito}) - \sum (\text{Descuentos})$$
* **Filtros requeridos:** Filtrar comprobantes anulados (`estado != 'ANULADO'`).
* **Dimensiones de análisis:** Por mes/año, por aseguradora (`id_cia`), por servicio médico, por tipo de paciente.

### B. Ticket Promedio de Atención
$$\text{Ticket Promedio} = \frac{\text{Facturación Total del Periodo}}{\text{Número de Admisiones Únicas Facturadas}}$$

### C. Distribución de Cartera por Aseguradora
$$\% \text{ Participación Cia}_i = \frac{\text{Facturación Cia}_i}{\text{Facturación Total}} \times 100$$
* Identifica la concentración de ingresos (ej. Rímac, Pacífico, Particulares, SIS).

---

## 2. Indicadores Asistenciales y Operativos

### A. Volumen de Atenciones (Admisiones)
* Conteo total de atenciones en `sisclin.atenciones` agrupadas por:
  - Tipo de atención: Emergencia, Ambulatorio, Hospitalización.
  - Especialidad o servicio médico.
  - Sede (si aplica).

### B. Tiempo de Estancia Hospitalaria (Días de Estancia)
$$\text{Días Estancia} = \text{Fecha Alta} - \text{Fecha Ingreso}$$
* Para pacientes hospitalizados (`tipo_atencion = 'HOSP'` o con cama asignada).
* **Promedio de Estancia (ALOS - Average Length of Stay):** $\frac{\text{Total días estancia}}{\text{Total altas hospitalarias}}$.

### C. Ocupación y Capacidad de Camas
$$\% \text{ Ocupación} = \frac{\text{Total días-cama ocupados}}{\text{Total camas disponibles} \times \text{Días del periodo}} \times 100$$

---

## 3. Indicadores de Laboratorio

### A. Volumen de Órdenes y Pruebas
* **Total Órdenes:** Conteo de `orden_id` únicos en `sislab.ordenes`.
* **Total Pruebas/Determinaciones:** Conteo de líneas en `sislab.ordenes_detalle`.
* **Ratio Pruebas / Orden:** $\frac{\text{Total Pruebas}}{\text{Total Órdenes}}$.

### B. Demanda por Origen
* Proporción de órdenes procedentes de Emergencia vs. Hospitalización vs. Consulta Externa.
