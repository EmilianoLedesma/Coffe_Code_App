from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.gastos_fijos import GastoFijo
from app.models.gastos_fijos import (
    AplicarGastoFijoOut,
    GastoFijoCreate,
    GastoFijoOut,
    GastoFijoUpdate,
)
from app.security.auth import TokenData, require_rol
from app.services.gastos_fijos import (
    aplicar_gasto_fijo,
    aplicar_todos_gastos_fijos,
    actualizar_gasto_fijo,
    crear_gasto_fijo,
)

router = APIRouter(prefix="/api/gastos-fijos", tags=["gastos-fijos"])

_solo_admin = require_rol(RolNombre.ADMINISTRADOR)


def _get_gasto_fijo_o_404(db: Session, gasto_fijo_id: int) -> GastoFijo:
    gasto_fijo = db.query(GastoFijo).filter(GastoFijo.id == gasto_fijo_id).first()
    if not gasto_fijo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto fijo no encontrado")
    return gasto_fijo


@router.get("", response_model=list[GastoFijoOut])
def listar(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> list[GastoFijo]:
    consulta = db.query(GastoFijo)
    if not incluir_inactivos:
        consulta = consulta.filter(GastoFijo.activo.is_(True))
    return consulta.order_by(GastoFijo.categoria, GastoFijo.concepto).all()


@router.post("", response_model=GastoFijoOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: GastoFijoCreate,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(_solo_admin),
) -> GastoFijo:
    return crear_gasto_fijo(db, datos, usuario.user_id)


@router.put("/{gasto_fijo_id}", response_model=GastoFijoOut)
def actualizar(
    gasto_fijo_id: int,
    datos: GastoFijoUpdate,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> GastoFijo:
    gasto_fijo = _get_gasto_fijo_o_404(db, gasto_fijo_id)
    return actualizar_gasto_fijo(db, gasto_fijo, datos)


@router.delete("/{gasto_fijo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    gasto_fijo_id: int, db: Session = Depends(get_db), _=Depends(_solo_admin)
) -> None:
    gasto_fijo = _get_gasto_fijo_o_404(db, gasto_fijo_id)
    db.delete(gasto_fijo)
    db.commit()


@router.post("/{gasto_fijo_id}/aplicar", response_model=AplicarGastoFijoOut)
def aplicar(
    gasto_fijo_id: int,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(_solo_admin),
) -> AplicarGastoFijoOut:
    gasto_fijo = _get_gasto_fijo_o_404(db, gasto_fijo_id)
    gasto = aplicar_gasto_fijo(db, gasto_fijo, usuario.user_id)
    return AplicarGastoFijoOut(
        gasto_id=gasto.id, concepto=gasto.concepto, monto=gasto.monto, fecha_gasto=gasto.fecha_gasto
    )


@router.post("/aplicar-todos", response_model=list[AplicarGastoFijoOut])
def aplicar_todos(
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(_solo_admin),
) -> list[AplicarGastoFijoOut]:
    gastos = aplicar_todos_gastos_fijos(db, usuario.user_id)
    return [
        AplicarGastoFijoOut(
            gasto_id=gasto.id, concepto=gasto.concepto, monto=gasto.monto, fecha_gasto=gasto.fecha_gasto
        )
        for gasto in gastos
    ]
