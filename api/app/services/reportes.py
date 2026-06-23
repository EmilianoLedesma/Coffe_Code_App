from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data.detalle_pedidos import DetallePedido
from app.data.gastos import Gasto
from app.data.pedidos import Pedido
from app.data.productos import Producto
from app.data.tickets import Ticket


def calcular_resumen_caja(db: Session, desde: datetime, hasta: datetime) -> dict:
    total_ventas = (
        db.query(func.coalesce(func.sum(Ticket.total), 0))
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
