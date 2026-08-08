from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.data.metodos_pago import MetodoPago
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.models.ventas import VentaCreate


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def registrar_venta(db: Session, datos: VentaCreate, usuario_id: int) -> Ticket:
    ticket = (
        db.query(Ticket)
        .options(joinedload(Ticket.pago))
        .filter(Ticket.id == datos.ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado")

    if ticket.pago:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El ticket ya tiene un pago registrado"
        )

    metodo = db.query(MetodoPago).filter(MetodoPago.nombre == datos.metodo_pago).first()
    if not metodo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Método de pago inválido: '{datos.metodo_pago}'",
        )

    if datos.monto < ticket.total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El monto recibido ({datos.monto}) es insuficiente para el total ({ticket.total})",
        )

    ticket.pago = Pago(
        monto_recibido=datos.monto,
        cambio=_redondear(datos.monto - ticket.total),
        id_metodo=metodo.id,
    )

    pedido = db.query(Pedido).filter(Pedido.id == ticket.id_pedido).first()
    pedido.total = ticket.total

    db.commit()
    db.refresh(ticket)
    return ticket
