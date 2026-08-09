from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.data.cortes_diarios import CorteDiario, CorteMetodoPago
from app.data.gastos import Gasto
from app.data.metodos_pago import MetodoPago
from app.data.pagos import Pago
from app.data.tickets import Ticket


def _rango_del_dia(fecha: date) -> tuple[datetime, datetime]:
    inicio = datetime.combine(fecha, time.min, tzinfo=timezone.utc)
    fin = datetime.combine(fecha, time.max, tzinfo=timezone.utc)
    return inicio, fin


def _calcular_totales(db: Session, fecha: date) -> dict:
    inicio, fin = _rango_del_dia(fecha)

    tickets = (
        db.query(func.coalesce(func.sum(Ticket.total), 0), func.count(Ticket.id))
        .join(Pago, Pago.id_ticket == Ticket.id)
        .filter(Ticket.fecha_emision >= inicio, Ticket.fecha_emision <= fin)
        .one()
    )
    total_ventas, num_tickets = Decimal(tickets[0]), tickets[1]

    total_gastos = (
        db.query(func.coalesce(func.sum(Gasto.monto), 0))
        .filter(Gasto.fecha_gasto >= inicio, Gasto.fecha_gasto <= fin)
        .scalar()
    )
    total_gastos = Decimal(total_gastos)

    num_pedidos = (
        db.query(func.count(func.distinct(Ticket.id_pedido)))
        .join(Pago, Pago.id_ticket == Ticket.id)
        .filter(Ticket.fecha_emision >= inicio, Ticket.fecha_emision <= fin)
        .scalar()
    )

    desglose = (
        db.query(MetodoPago.id, func.coalesce(func.sum(Ticket.total), 0))
        .join(Pago, Pago.id_metodo == MetodoPago.id)
        .join(Ticket, Ticket.id == Pago.id_ticket)
        .filter(Ticket.fecha_emision >= inicio, Ticket.fecha_emision <= fin)
        .group_by(MetodoPago.id)
        .all()
    )

    return {
        "total_ventas": total_ventas,
        "total_gastos": total_gastos,
        "ganancia_neta": total_ventas - total_gastos,
        "num_pedidos": num_pedidos,
        "num_tickets": num_tickets,
        "desglose": [{"id_metodo_pago": id_metodo, "monto": Decimal(monto)} for id_metodo, monto in desglose],
    }


def generar_o_actualizar_corte(db: Session, fecha: date, id_usuario: int) -> CorteDiario:
    totales = _calcular_totales(db, fecha)

    corte = db.query(CorteDiario).filter(CorteDiario.fecha == fecha).first()
    if corte is None:
        corte = CorteDiario(fecha=fecha, id_usuario=id_usuario, **{
            k: v for k, v in totales.items() if k != "desglose"
        })
        db.add(corte)
        db.flush()
    else:
        for campo in ("total_ventas", "total_gastos", "ganancia_neta", "num_pedidos", "num_tickets"):
            setattr(corte, campo, totales[campo])
        corte.id_usuario = id_usuario
        db.query(CorteMetodoPago).filter(CorteMetodoPago.id_corte == corte.id).delete()
        db.flush()

    for fila in totales["desglose"]:
        db.add(CorteMetodoPago(id_corte=corte.id, id_metodo_pago=fila["id_metodo_pago"], monto=fila["monto"]))

    db.commit()
    db.refresh(corte)
    return corte


def obtener_corte(db: Session, fecha: date) -> CorteDiario | None:
    return (
        db.query(CorteDiario)
        .options(joinedload(CorteDiario.desglose_metodos).joinedload(CorteMetodoPago.metodo))
        .filter(CorteDiario.fecha == fecha)
        .first()
    )


def listar_cortes(db: Session, desde: date, hasta: date) -> list[CorteDiario]:
    return (
        db.query(CorteDiario)
        .filter(CorteDiario.fecha >= desde, CorteDiario.fecha <= hasta)
        .order_by(CorteDiario.fecha.desc())
        .all()
    )
