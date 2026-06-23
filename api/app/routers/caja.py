from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.pagos import Pago
from app.data.tickets import Ticket
from app.models.ventas import (
    CompraCreate,
    CompraOut,
    GastoCreate,
    GastoOut,
    ResumenCaja,
    TicketOut,
    VentaCreate,
)
from app.security.auth import TokenData, require_rol
from app.services.gastos import registrar_compra, registrar_gasto
from app.services.reportes import calcular_resumen_caja
from app.services.ventas import registrar_venta

router = APIRouter(tags=["caja"])

_requiere_caja = require_rol(RolNombre.CAJERO, RolNombre.ADMINISTRADOR)


@router.post("/ventas", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def crear_venta(
    datos: VentaCreate,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(_requiere_caja),
) -> Ticket:
    ticket = registrar_venta(db, datos, usuario_id=usuario.user_id)
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.pago).joinedload(Pago.metodo))
        .filter(Ticket.id == ticket.id)
        .first()
    )


@router.post("/gastos", response_model=GastoOut, status_code=status.HTTP_201_CREATED)
def crear_gasto(
    datos: GastoCreate,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(_requiere_caja),
) -> GastoOut:
    return registrar_gasto(db, datos, usuario_id=usuario.user_id)


@router.post("/compras", response_model=CompraOut, status_code=status.HTTP_201_CREATED)
def crear_compra(
    datos: CompraCreate,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(_requiere_caja),
) -> CompraOut:
    gasto, nuevo_stock = registrar_compra(db, datos, usuario_id=usuario.user_id)
    return CompraOut(gasto=GastoOut.model_validate(gasto), ingrediente_id=datos.ingrediente_id, nuevo_stock=nuevo_stock)


@router.get("/caja/resumen", response_model=ResumenCaja)
def resumen_caja(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _usuario: TokenData = Depends(_requiere_caja),
) -> dict:
    hasta = hasta or datetime.now(timezone.utc)
    desde = desde or (hasta - timedelta(days=1))
    return calcular_resumen_caja(db, desde, hasta)
