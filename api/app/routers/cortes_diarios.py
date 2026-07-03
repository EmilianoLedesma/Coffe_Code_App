from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.db import get_db
from app.models.cortes_diarios import CorteDiarioOut, DesgloseMetodoPagoOut
from app.security.auth import TokenData, require_rol
from app.services.cortes_diarios import generar_o_actualizar_corte, listar_cortes, obtener_corte

router = APIRouter(prefix="/api/cortes-diarios", tags=["cortes-diarios"])

_solo_admin = require_rol(RolNombre.ADMINISTRADOR)


def _serializar(corte) -> CorteDiarioOut:
    return CorteDiarioOut(
        id=corte.id,
        fecha=corte.fecha,
        total_ventas=corte.total_ventas,
        total_gastos=corte.total_gastos,
        ganancia_neta=corte.ganancia_neta,
        num_pedidos=corte.num_pedidos,
        num_tickets=corte.num_tickets,
        generado_en=corte.generado_en,
        desglose_metodos=[
            DesgloseMetodoPagoOut(metodo_pago=d.metodo.nombre, monto=d.monto) for d in corte.desglose_metodos
        ],
    )


@router.post("", response_model=CorteDiarioOut)
def generar(
    fecha: date | None = None,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(_solo_admin),
) -> CorteDiarioOut:
    fecha = fecha or date.today()
    corte = generar_o_actualizar_corte(db, fecha, usuario.user_id)
    return _serializar(corte)


@router.get("", response_model=list[CorteDiarioOut])
def listar(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> list[CorteDiarioOut]:
    hasta = hasta or date.today()
    desde = desde or (hasta - timedelta(days=30))
    return [_serializar(c) for c in listar_cortes(db, desde, hasta)]


@router.get("/{fecha}", response_model=CorteDiarioOut)
def obtener(fecha: date, db: Session = Depends(get_db), _=Depends(_solo_admin)) -> CorteDiarioOut:
    corte = obtener_corte(db, fecha)
    if corte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay corte generado para esa fecha")
    return _serializar(corte)
