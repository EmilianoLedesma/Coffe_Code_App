from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.detalle_pedidos import DetallePedido
from app.data.estatus_pedidos import EstatusPedido
from app.data.pedidos import Pedido
from app.models.pedidos import CambioEstadoPedido, PedidoCreate, PedidoOut
from app.security.auth import require_rol
from app.services.pedidos import cambiar_estado_pedido, crear_pedido

router = APIRouter(prefix="/pedidos", tags=["pedidos"])

_PEDIDO_LOAD_OPTIONS = (
    joinedload(Pedido.estatus),
    joinedload(Pedido.detalle).joinedload(DetallePedido.producto),
    joinedload(Pedido.detalle).joinedload(DetallePedido.estatus),
)


def _get_pedido_o_404(db: Session, pedido_id: int) -> Pedido:
    pedido = db.query(Pedido).options(*_PEDIDO_LOAD_OPTIONS).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    return pedido


@router.post("", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: PedidoCreate,
    db: Session = Depends(get_db),
    _=Depends(require_rol(RolNombre.MESERO, RolNombre.ADMINISTRADOR)),
) -> Pedido:
    pedido = crear_pedido(db, datos)
    return _get_pedido_o_404(db, pedido.id)


@router.get("", response_model=list[PedidoOut])
def listar(
    estado: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _=Depends(
        require_rol(
            RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR
        )
    ),
) -> list[Pedido]:
    query = db.query(Pedido).options(*_PEDIDO_LOAD_OPTIONS)
    if estado:
        query = query.join(EstatusPedido).filter(EstatusPedido.nombre == estado)
    return query.order_by(Pedido.fecha.asc()).offset(offset).limit(limit).all()


@router.get("/{pedido_id}", response_model=PedidoOut)
def obtener(
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(
        require_rol(
            RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR
        )
    ),
) -> Pedido:
    return _get_pedido_o_404(db, pedido_id)


@router.put("/{pedido_id}/estado", response_model=PedidoOut)
def cambiar_estado(
    pedido_id: int,
    datos: CambioEstadoPedido,
    db: Session = Depends(get_db),
    _=Depends(
        require_rol(
            RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR
        )
    ),
) -> Pedido:
    pedido = _get_pedido_o_404(db, pedido_id)
    pedido, _alertas = cambiar_estado_pedido(db, pedido, datos.estatus)
    return _get_pedido_o_404(db, pedido.id)
