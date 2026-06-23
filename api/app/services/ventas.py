from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.data.metodos_pago import MetodoPago
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.models.ventas import VentaCreate


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def registrar_venta(db: Session, datos: VentaCreate, usuario_id: int) -> Ticket:
    pedido = db.query(Pedido).filter(Pedido.id == datos.pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    if not pedido.detalle:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pedido no tiene ítems")

    ticket_existente = db.query(Ticket).filter(Ticket.id_pedido == pedido.id).first()
    if ticket_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El pedido ya tiene un pago registrado",
        )

    metodo = db.query(MetodoPago).filter(MetodoPago.nombre == datos.metodo_pago).first()
    if not metodo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Método de pago inválido: '{datos.metodo_pago}'",
        )

    subtotal = sum((d.precio_unitario * d.cantidad for d in pedido.detalle), Decimal("0"))
    iva = _redondear(subtotal * Decimal(str(settings.iva_rate)))
    total = _redondear(subtotal + iva)

    if datos.monto < total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El monto recibido ({datos.monto}) es insuficiente para el total ({total})",
        )

    ticket = Ticket(
        subtotal=_redondear(subtotal),
        iva=iva,
        total=total,
        id_pedido=pedido.id,
        id_usuario=usuario_id,
    )
    ticket.pago = Pago(
        monto_recibido=datos.monto,
        cambio=_redondear(datos.monto - total),
        id_metodo=metodo.id,
    )

    pedido.total = total

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket
