from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import EstatusPedidoNombre
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.websockets.manager import manager


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_totales(pedido: Pedido) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum((d.precio_unitario * d.cantidad for d in pedido.detalle), Decimal("0"))
    iva = _redondear(subtotal * Decimal(str(settings.iva_rate)))
    total = _redondear(subtotal + iva)
    return _redondear(subtotal), iva, total


def cerrar_cuenta(db: Session, pedido: Pedido, usuario_id: int) -> Ticket:
    if pedido.estatus.nombre != EstatusPedidoNombre.LISTO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede cerrar la cuenta de un pedido Listo",
        )

    ticket_existente = db.query(Ticket).filter(Ticket.id_pedido == pedido.id).first()
    if ticket_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La cuenta de este pedido ya fue cerrada"
        )

    subtotal, iva, total = calcular_totales(pedido)
    ticket = Ticket(subtotal=subtotal, iva=iva, total=total, id_pedido=pedido.id, id_usuario=usuario_id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    manager.emitir(
        "caja",
        {"evento": "cuenta_cerrada", "pedido_id": pedido.id, "mesa_id": pedido.id_mesa},
    )
    return ticket
