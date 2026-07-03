from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data.detalle_pedidos import DetallePedido
from app.data.gastos import Gasto
from app.data.ingredientes import Ingrediente
from app.data.pedidos import Pedido
from app.data.productos import Producto
from app.data.recetas import Receta
from app.data.tickets import Ticket


def calcular_resumen_caja(db: Session, desde: datetime, hasta: datetime) -> dict:
    total_ventas = (
        db.query(func.coalesce(func.sum(Ticket.subtotal), 0))
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .scalar()
    )
    total_gastos = (
        db.query(func.coalesce(func.sum(Gasto.monto), 0))
        .filter(Gasto.fecha_gasto >= desde, Gasto.fecha_gasto <= hasta)
        .scalar()
    )
    total_ventas = Decimal(total_ventas)
    total_gastos = Decimal(total_gastos)

    return {
        "desde": desde,
        "hasta": hasta,
        "total_ventas": total_ventas,
        "total_gastos": total_gastos,
        "ganancia_neta": total_ventas - total_gastos,
    }


def calcular_top_productos(db: Session, desde: datetime, hasta: datetime, limite: int = 5) -> list[dict]:
    filas = (
        db.query(
            Producto.id.label("producto_id"),
            Producto.nombre.label("nombre"),
            func.coalesce(func.sum(DetallePedido.cantidad), 0).label("cantidad_vendida"),
            func.coalesce(func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario), 0).label(
                "ingresos"
            ),
        )
        .join(DetallePedido, DetallePedido.id_producto == Producto.id)
        .join(Pedido, Pedido.id == DetallePedido.id_pedido)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(Producto.id, Producto.nombre)
        .order_by(func.sum(DetallePedido.cantidad).desc())
        .limit(limite)
        .all()
    )
    return [
        {
            "producto_id": fila.producto_id,
            "nombre": fila.nombre,
            "cantidad_vendida": int(fila.cantidad_vendida),
            "ingresos": Decimal(fila.ingresos),
        }
        for fila in filas
    ]


def calcular_reporte_admin(db: Session, desde: datetime, hasta: datetime) -> dict:
    resumen = calcular_resumen_caja(db, desde, hasta)
    resumen["top_productos"] = calcular_top_productos(db, desde, hasta)
    return resumen


def periodo_anterior(desde: datetime, hasta: datetime) -> tuple[datetime, datetime]:
    duracion = hasta - desde
    return desde - duracion, desde


def _dec(valor) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def calcular_margen_pct(total_ventas, ganancia_neta) -> Decimal:
    total_ventas = _dec(total_ventas)
    ganancia_neta = _dec(ganancia_neta)
    if total_ventas == 0:
        return Decimal("0")
    return (ganancia_neta / total_ventas * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def variacion_pct(actual, anterior) -> Decimal | None:
    actual = _dec(actual)
    anterior = _dec(anterior)
    if anterior == 0:
        return None
    return ((actual - anterior) / anterior * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def costo_receta_producto(db: Session, producto_id: int) -> Decimal:
    filas = (
        db.query(Receta.cantidad_requerida, Ingrediente.costo_unitario)
        .join(Ingrediente, Receta.id_ingrediente == Ingrediente.id)
        .filter(Receta.id_producto == producto_id)
        .all()
    )
    total = Decimal("0")
    for cantidad_requerida, costo_unitario in filas:
        total += _dec(cantidad_requerida) * _dec(costo_unitario)
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_ranking_margen(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    top_productos = calcular_top_productos(db, desde, hasta)
    filas = []
    for producto in top_productos:
        cantidad = producto["cantidad_vendida"] or 1
        ingresos = producto["ingresos"]
        costo_unitario_total = costo_receta_producto(db, producto["producto_id"])
        costo_total = (costo_unitario_total * cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        margen = ingresos - costo_total
        margen_pct = calcular_margen_pct(ingresos, margen)
        filas.append(
            {
                "producto_id": producto["producto_id"],
                "nombre": producto["nombre"],
                "ingresos": ingresos,
                "costo_total": costo_total,
                "margen": margen,
                "margen_pct": margen_pct,
            }
        )
    return sorted(filas, key=lambda fila: fila["margen_pct"])


def calcular_riesgo_inventario(db: Session) -> list[dict]:
    ingredientes_bajo_stock = (
        db.query(Ingrediente)
        .filter(Ingrediente.activo.is_(True), Ingrediente.stock_actual < Ingrediente.stock_minimo)
        .all()
    )
    filas = []
    for ingrediente in ingredientes_bajo_stock:
        productos_afectados = (
            db.query(Producto.nombre)
            .join(Receta, Receta.id_producto == Producto.id)
            .filter(Receta.id_ingrediente == ingrediente.id)
            .order_by(Producto.nombre)
            .all()
        )
        nombres = [nombre for (nombre,) in productos_afectados]
        falta = ingrediente.stock_minimo - ingrediente.stock_actual
        costo_reposicion = (falta * ingrediente.costo_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        filas.append(
            {
                "id": ingrediente.id,
                "nombre": ingrediente.nombre,
                "unidad": ingrediente.unidad,
                "stock_actual": ingrediente.stock_actual,
                "stock_minimo": ingrediente.stock_minimo,
                "falta": falta,
                "costo_reposicion": costo_reposicion,
                "productos_afectados": nombres,
            }
        )
    return sorted(filas, key=lambda fila: fila["falta"], reverse=True)


def construir_reporte_financiero(db: Session, desde: datetime, hasta: datetime) -> dict:
    reporte_actual = calcular_reporte_admin(db, desde, hasta)
    desde_prev, hasta_prev = periodo_anterior(desde, hasta)
    reporte_anterior = calcular_reporte_admin(db, desde_prev, hasta_prev)

    margen_pct = calcular_margen_pct(reporte_actual["total_ventas"], reporte_actual["ganancia_neta"])
    margen_pct_anterior = calcular_margen_pct(reporte_anterior["total_ventas"], reporte_anterior["ganancia_neta"])
    variacion_ventas_pct = variacion_pct(reporte_actual["total_ventas"], reporte_anterior["total_ventas"])
    variacion_ganancia_pct = variacion_pct(reporte_actual["ganancia_neta"], reporte_anterior["ganancia_neta"])
    ranking_margen = calcular_ranking_margen(db, desde, hasta)

    return {
        "desde": desde,
        "hasta": hasta,
        "total_ventas": reporte_actual["total_ventas"],
        "total_gastos": reporte_actual["total_gastos"],
        "ganancia_neta": reporte_actual["ganancia_neta"],
        "margen_pct": margen_pct,
        "margen_pct_anterior": margen_pct_anterior,
        "variacion_ventas_pct": variacion_ventas_pct,
        "variacion_ganancia_pct": variacion_ganancia_pct,
        "ranking_margen": ranking_margen,
    }


def construir_reporte_inventario(db: Session) -> dict:
    return {"riesgo": calcular_riesgo_inventario(db)}
