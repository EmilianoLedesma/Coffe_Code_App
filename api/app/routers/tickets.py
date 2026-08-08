from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.models.ventas import TicketOut
from app.security.auth import TokenData, require_rol

router = APIRouter(prefix="/tickets", tags=["tickets"])

_TICKET_LOAD_OPTIONS = (joinedload(Ticket.pago).joinedload(Pago.metodo),)


@router.get("", response_model=list[TicketOut])
def listar(
    pagado: bool | None = None,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(
        require_rol(RolNombre.MESERO, RolNombre.CAJERO, RolNombre.ADMINISTRADOR)
    ),
) -> list[Ticket]:
    query = db.query(Ticket).options(*_TICKET_LOAD_OPTIONS)

    if usuario.rol == RolNombre.MESERO:
        query = query.join(Pedido, Ticket.id_pedido == Pedido.id).filter(
            Pedido.id_usuario == usuario.user_id
        )

    if pagado is True:
        query = query.join(Pago, Ticket.id == Pago.id_ticket)
    elif pagado is False:
        query = query.outerjoin(Pago, Ticket.id == Pago.id_ticket).filter(Pago.id.is_(None))

    return query.order_by(Ticket.fecha_emision.desc()).all()
