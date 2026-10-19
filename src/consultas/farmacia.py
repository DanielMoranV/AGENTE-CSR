"""
Módulo de Consultas de Farmacia (SISCLIN) para AGENTE-CSR.
Solo lectura. Proporciona consultas consolidadas de órdenes de compra, proveedores y adquisiciones.
"""

from typing import Optional, Dict, Any
import pandas as pd

from src.database.connection import ejecutar_consulta_autorizada


def consultar_compras_farmacia_por_proveedor(
    fecha_inicio: str,
    fecha_fin: str,
    usuario_sesion: Optional[str] = None,
    usar_datos_sinteticos_si_no_db: bool = False
) -> pd.DataFrame:
    """
    Obtiene el consolidado de compras a proveedores de farmacia en un rango de fechas.
    Retorna: proveedor, ruc, total_ocs, total_items, monto_total y participacion_pct.
    """
    sql = """
    WITH compras AS (
        SELECT 
            p.codigo_proveedor,
            p.nombre AS proveedor,
            p.ruc,
            COUNT(DISTINCT oc.id) AS total_ocs,
            COUNT(det.id) AS total_items,
            ROUND(SUM(det.cantidad * det.precio_compra)::numeric, 2) AS monto_total
        FROM sisclin.ordenes_compra_farmacia oc
        JOIN sisclin.proveedores_farmacia p ON oc.proveedor_id = p.id
        JOIN sisclin.detalle_ordenes_compra_farmacia det ON oc.id = det.orden_compra_id
        WHERE oc.fecha >= :fecha_inicio 
          AND oc.fecha <= :fecha_fin
        GROUP BY p.codigo_proveedor, p.nombre, p.ruc
    )
    SELECT 
        codigo_proveedor,
        proveedor,
        ruc,
        total_ocs,
        total_items,
        monto_total,
        ROUND((monto_total * 100.0 / NULLIF(SUM(monto_total) OVER(), 0))::numeric, 2) AS participacion_pct
    FROM compras
    ORDER BY monto_total DESC
    """
    params = {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin}

    try:
        df = ejecutar_consulta_autorizada(
            operacion_id="compras_farmacia_por_proveedor",
            sql_parametrizado=sql,
            parametros=params,
            limite_filas=500,
            usuario_sesion=usuario_sesion
        )
        return df
    except Exception:
        if usar_datos_sinteticos_si_no_db:
            return pd.DataFrame()
        raise


def consultar_productos_costosos_farmacia(
    fecha_inicio: str,
    fecha_fin: str,
    orden_por: str = "precio_unitario",
    top: int = 10,
    usuario_sesion: Optional[str] = None
) -> pd.DataFrame:
    """
    Obtiene el ranking de productos más costosos adquiridos en farmacia.
    Args:
        orden_por: 'precio_unitario' (costo por unidad) o 'monto_total' (desembolso acumulado).
    """
    if orden_por == "precio_unitario":
        sql = """
        SELECT 
            det.codigo_producto,
            pr.nombre_producto,
            pr.unidad,
            p.nombre AS proveedor,
            ROUND(det.precio_compra::numeric, 2) AS precio_unitario,
            det.cantidad,
            ROUND((det.cantidad * det.precio_compra)::numeric, 2) AS subtotal_linea,
            oc.id_oc,
            oc.fecha
        FROM sisclin.detalle_ordenes_compra_farmacia det
        JOIN sisclin.ordenes_compra_farmacia oc ON det.orden_compra_id = oc.id
        JOIN sisclin.productos_farmacia pr ON det.producto_id = pr.id
        JOIN sisclin.proveedores_farmacia p ON oc.proveedor_id = p.id
        WHERE oc.fecha >= :fecha_inicio 
          AND oc.fecha <= :fecha_fin
        ORDER BY det.precio_compra DESC
        """
    else:
        sql = """
        SELECT 
            det.codigo_producto,
            pr.nombre_producto,
            SUM(det.cantidad) AS cantidad_total,
            ROUND(AVG(det.precio_compra)::numeric, 2) AS precio_unitario_promedio,
            ROUND(SUM(det.cantidad * det.precio_compra)::numeric, 2) AS monto_total_comprado
        FROM sisclin.detalle_ordenes_compra_farmacia det
        JOIN sisclin.ordenes_compra_farmacia oc ON det.orden_compra_id = oc.id
        JOIN sisclin.productos_farmacia pr ON det.producto_id = pr.id
        WHERE oc.fecha >= :fecha_inicio 
          AND oc.fecha <= :fecha_fin
        GROUP BY det.codigo_producto, pr.nombre_producto
        ORDER BY monto_total_comprado DESC
        """

    params = {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin}
    return ejecutar_consulta_autorizada(
        operacion_id="productos_costosos_farmacia",
        sql_parametrizado=sql,
        parametros=params,
        limite_filas=top,
        usuario_sesion=usuario_sesion
    )
