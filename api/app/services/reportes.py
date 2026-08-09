from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.data.categorias import Categoria
from app.data.detalle_pedidos import DetallePedido
from app.data.estatus_pedidos import EstatusPedido
from app.data.gastos import Gasto
from app.data.ingredientes import Ingrediente
from app.data.mesas import Mesa
from app.data.metodos_pago import MetodoPago
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.productos import Producto
from app.data.recetas import Receta
from app.data.tickets import Ticket
from app.data.usuarios import Usuario


def calcular_resumen_caja(db: Session, desde: datetime, hasta: datetime) -> dict:
    total_ventas = (
        db.query(func.coalesce(func.sum(Ticket.total), 0))
        .join(Pago, Pago.id_ticket == Ticket.id)
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
        .join(Pago, Pago.id_ticket == Ticket.id)
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


def calcular_ventas_por_categoria(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            Categoria.id.label("categoria_id"),
            Categoria.nombre.label("nombre"),
            func.coalesce(func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario), 0).label("total"),
        )
        .join(Producto, Producto.id_categoria == Categoria.id)
        .join(DetallePedido, DetallePedido.id_producto == Producto.id)
        .join(Pedido, Pedido.id == DetallePedido.id_pedido)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .join(Pago, Pago.id_ticket == Ticket.id)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(Categoria.id, Categoria.nombre)
        .order_by(func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario).desc())
        .all()
    )
    return [
        {"categoria_id": fila.categoria_id, "nombre": fila.nombre, "total": Decimal(fila.total)}
        for fila in filas
    ]


def calcular_ventas_por_usuario(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            Usuario.id.label("usuario_id"),
            Usuario.nombre.label("nombre"),
            func.coalesce(func.sum(Ticket.total), 0).label("total"),
        )
        .join(Pedido, Pedido.id_usuario == Usuario.id)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .join(Pago, Pago.id_ticket == Ticket.id)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(Usuario.id, Usuario.nombre)
        .order_by(func.sum(Ticket.total).desc())
        .all()
    )
    return [
        {"usuario_id": fila.usuario_id, "nombre": fila.nombre, "total": Decimal(fila.total)}
        for fila in filas
    ]


def calcular_ventas_por_metodo_pago(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            MetodoPago.nombre.label("metodo_pago"),
            func.coalesce(func.sum(Ticket.total), 0).label("total"),
        )
        .join(Pago, Pago.id_metodo == MetodoPago.id)
        .join(Ticket, Ticket.id == Pago.id_ticket)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(MetodoPago.nombre)
        .order_by(func.sum(Ticket.total).desc())
        .all()
    )
    return [{"metodo_pago": fila.metodo_pago, "total": Decimal(fila.total)} for fila in filas]


def calcular_detalle_ventas(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            Ticket.fecha_emision.label("fecha"),
            Pedido.id.label("pedido_id"),
            Mesa.numero_mesa.label("mesa"),
            Usuario.nombre.label("mesero"),
            Producto.nombre.label("producto"),
            DetallePedido.cantidad.label("cantidad"),
            DetallePedido.precio_unitario.label("precio_unitario"),
        )
        .join(Pedido, Pedido.id == DetallePedido.id_pedido)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .join(Pago, Pago.id_ticket == Ticket.id)
        .join(Mesa, Mesa.id == Pedido.id_mesa)
        .join(Usuario, Usuario.id == Pedido.id_usuario)
        .join(Producto, Producto.id == DetallePedido.id_producto)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .order_by(Ticket.fecha_emision.desc())
        .all()
    )
    return [
        {
            "fecha": fila.fecha,
            "pedido_id": fila.pedido_id,
            "mesa": fila.mesa,
            "mesero": fila.mesero,
            "producto": fila.producto,
            "cantidad": fila.cantidad,
            "precio_unitario": fila.precio_unitario,
            "subtotal": (_dec(fila.precio_unitario) * fila.cantidad).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
        }
        for fila in filas
    ]


_PREFIJO_COMPRA_INSUMO = "Compra de insumo:"
_PREFIJO_GASTO_FIJO = "Gasto fijo:"


def calcular_gastos_por_tipo(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(Gasto.concepto, Gasto.monto)
        .filter(Gasto.fecha_gasto >= desde, Gasto.fecha_gasto <= hasta)
        .all()
    )
    totales = {
        "Compras de insumos": Decimal("0"),
        "Gastos fijos": Decimal("0"),
        "Otros gastos": Decimal("0"),
    }
    for concepto, monto in filas:
        if concepto.startswith(_PREFIJO_COMPRA_INSUMO):
            clave = "Compras de insumos"
        elif concepto.startswith(_PREFIJO_GASTO_FIJO):
            clave = "Gastos fijos"
        else:
            clave = "Otros gastos"
        totales[clave] += _dec(monto)
    return [{"tipo": tipo, "total": total} for tipo, total in totales.items()]


def calcular_gastos_por_usuario(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            Usuario.id.label("usuario_id"),
            Usuario.nombre.label("nombre"),
            func.coalesce(func.sum(Gasto.monto), 0).label("total"),
        )
        .join(Gasto, Gasto.id_usuario == Usuario.id)
        .filter(Gasto.fecha_gasto >= desde, Gasto.fecha_gasto <= hasta)
        .group_by(Usuario.id, Usuario.nombre)
        .order_by(func.sum(Gasto.monto).desc())
        .all()
    )
    return [
        {"usuario_id": fila.usuario_id, "nombre": fila.nombre, "total": Decimal(fila.total)}
        for fila in filas
    ]


def calcular_detalle_gastos(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(Gasto)
        .options(joinedload(Gasto.usuario))
        .filter(Gasto.fecha_gasto >= desde, Gasto.fecha_gasto <= hasta)
        .order_by(Gasto.fecha_gasto.desc())
        .all()
    )
    return [
        {
            "id": gasto.id,
            "concepto": gasto.concepto,
            "monto": gasto.monto,
            "fecha_gasto": gasto.fecha_gasto,
            "usuario": gasto.usuario.nombre,
        }
        for gasto in filas
    ]


def calcular_ranking_consumo(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            Ingrediente.id.label("ingrediente_id"),
            Ingrediente.nombre.label("nombre"),
            Ingrediente.unidad.label("unidad"),
            func.coalesce(func.sum(DetallePedido.cantidad * Receta.cantidad_requerida), 0).label(
                "cantidad_consumida"
            ),
        )
        .join(Receta, Receta.id_ingrediente == Ingrediente.id)
        .join(DetallePedido, DetallePedido.id_producto == Receta.id_producto)
        .join(Pedido, Pedido.id == DetallePedido.id_pedido)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .join(Pago, Pago.id_ticket == Ticket.id)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(Ingrediente.id, Ingrediente.nombre, Ingrediente.unidad)
        .order_by(func.sum(DetallePedido.cantidad * Receta.cantidad_requerida).desc())
        .all()
    )
    return [
        {
            "ingrediente_id": fila.ingrediente_id,
            "nombre": fila.nombre,
            "unidad": fila.unidad,
            "cantidad_consumida": Decimal(fila.cantidad_consumida),
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


def construir_reporte_financiero(
    db: Session,
    desde: datetime,
    hasta: datetime,
    categoria_id: int | None = None,
    usuario_id: int | None = None,
) -> dict:
    reporte_actual = calcular_reporte_admin(db, desde, hasta)
    desde_prev, hasta_prev = periodo_anterior(desde, hasta)
    reporte_anterior = calcular_reporte_admin(db, desde_prev, hasta_prev)

    margen_pct = calcular_margen_pct(reporte_actual["total_ventas"], reporte_actual["ganancia_neta"])
    margen_pct_anterior = calcular_margen_pct(reporte_anterior["total_ventas"], reporte_anterior["ganancia_neta"])
    variacion_ventas_pct = variacion_pct(reporte_actual["total_ventas"], reporte_anterior["total_ventas"])
    variacion_ganancia_pct = variacion_pct(reporte_actual["ganancia_neta"], reporte_anterior["ganancia_neta"])

    ranking_margen = calcular_ranking_margen(db, desde, hasta)
    if categoria_id is not None:
        ranking_margen = [
            fila
            for fila in ranking_margen
            if db.query(Producto.id_categoria).filter(Producto.id == fila["producto_id"]).scalar() == categoria_id
        ]

    ventas_por_usuario = calcular_ventas_por_usuario(db, desde, hasta)
    if usuario_id is not None:
        ventas_por_usuario = [fila for fila in ventas_por_usuario if fila["usuario_id"] == usuario_id]

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
        "ventas_por_categoria": calcular_ventas_por_categoria(db, desde, hasta),
        "ventas_por_usuario": ventas_por_usuario,
        "ventas_por_metodo_pago": calcular_ventas_por_metodo_pago(db, desde, hasta),
        "detalle_ventas": calcular_detalle_ventas(db, desde, hasta),
        "gastos_por_tipo": calcular_gastos_por_tipo(db, desde, hasta),
        "gastos_por_usuario": calcular_gastos_por_usuario(db, desde, hasta),
        "detalle_gastos": calcular_detalle_gastos(db, desde, hasta),
    }


def construir_reporte_inventario(
    db: Session, desde: datetime | None = None, hasta: datetime | None = None
) -> dict:
    resultado = {"riesgo": calcular_riesgo_inventario(db)}
    if desde is not None and hasta is not None:
        resultado["ranking_consumo"] = calcular_ranking_consumo(db, desde, hasta)
    else:
        resultado["ranking_consumo"] = []
    return resultado


def calcular_catalogo_productos(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    ventas = (
        db.query(
            DetallePedido.id_producto.label("producto_id"),
            func.coalesce(func.sum(DetallePedido.cantidad), 0).label("cantidad_vendida"),
            func.coalesce(func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario), 0).label("ingresos"),
        )
        .join(Pedido, Pedido.id == DetallePedido.id_pedido)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .join(Pago, Pago.id_ticket == Ticket.id)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(DetallePedido.id_producto)
        .subquery()
    )

    filas = (
        db.query(
            Producto.id,
            Producto.nombre,
            Producto.disponible,
            Categoria.nombre.label("categoria"),
            func.coalesce(ventas.c.cantidad_vendida, 0).label("cantidad_vendida"),
            func.coalesce(ventas.c.ingresos, 0).label("ingresos"),
        )
        .join(Categoria, Categoria.id == Producto.id_categoria)
        .outerjoin(ventas, ventas.c.producto_id == Producto.id)
        .filter(Producto.activo.is_(True))
        .order_by(func.coalesce(ventas.c.cantidad_vendida, 0).desc())
        .all()
    )

    resultado = []
    for fila in filas:
        cantidad_vendida = int(fila.cantidad_vendida)
        ingresos = Decimal(fila.ingresos)
        costo_unitario_total = costo_receta_producto(db, fila.id)
        costo_total = (costo_unitario_total * cantidad_vendida).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        margen = ingresos - costo_total
        margen_pct = calcular_margen_pct(ingresos, margen)
        resultado.append(
            {
                "producto_id": fila.id,
                "nombre": fila.nombre,
                "categoria": fila.categoria,
                "disponible": fila.disponible,
                "cantidad_vendida": cantidad_vendida,
                "ingresos": ingresos,
                "costo_total": costo_total,
                "margen": margen,
                "margen_pct": margen_pct,
            }
        )
    return resultado


def construir_reporte_productos(db: Session, desde: datetime, hasta: datetime) -> dict:
    return {
        "desde": desde,
        "hasta": hasta,
        "productos": calcular_catalogo_productos(db, desde, hasta),
    }


def calcular_listado_pedidos(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            Pedido.id,
            Pedido.fecha,
            Pedido.total,
            Ticket.total.label("total_ticket"),
            Mesa.numero_mesa,
            Usuario.nombre,
            Usuario.apellido_paterno,
            EstatusPedido.nombre.label("estatus"),
        )
        .join(Mesa, Mesa.id == Pedido.id_mesa)
        .join(Usuario, Usuario.id == Pedido.id_usuario)
        .join(EstatusPedido, EstatusPedido.id == Pedido.id_estatus)
        .outerjoin(Ticket, Ticket.id_pedido == Pedido.id)
        .filter(Pedido.fecha >= desde, Pedido.fecha <= hasta)
        .order_by(Pedido.fecha)
        .all()
    )
    resultado = []
    for fila in filas:
        total = fila.total_ticket if fila.total_ticket is not None else fila.total
        resultado.append(
            {
                "pedido_id": fila.id,
                "fecha": fila.fecha,
                "mesa": fila.numero_mesa,
                "mesero": f"{fila.nombre} {fila.apellido_paterno}",
                "estatus": fila.estatus,
                "total": Decimal(total) if total is not None else Decimal("0"),
            }
        )
    return resultado


def construir_reporte_pedidos(db: Session, desde: datetime, hasta: datetime) -> dict:
    pedidos = calcular_listado_pedidos(db, desde, hasta)
    total_ventas = sum((fila["total"] for fila in pedidos), Decimal("0"))
    return {
        "desde": desde,
        "hasta": hasta,
        "total_pedidos": len(pedidos),
        "total_ventas": total_ventas,
        "pedidos": pedidos,
    }
