from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.data.gastos import Gasto
from app.data.gastos_fijos import GastoFijo
from app.models.gastos_fijos import GastoFijoCreate, GastoFijoUpdate

PREFIJO_GASTO_FIJO = "Gasto fijo:"


def crear_gasto_fijo(db: Session, datos: GastoFijoCreate, usuario_id: int) -> GastoFijo:
    gasto_fijo = GastoFijo(
        concepto=datos.concepto,
        monto=datos.monto,
        categoria=datos.categoria,
        id_usuario=usuario_id,
    )
    db.add(gasto_fijo)
    db.commit()
    db.refresh(gasto_fijo)
    return gasto_fijo


def actualizar_gasto_fijo(db: Session, gasto_fijo: GastoFijo, datos: GastoFijoUpdate) -> GastoFijo:
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(gasto_fijo, campo, valor)
    db.commit()
    db.refresh(gasto_fijo)
    return gasto_fijo


def aplicar_gasto_fijo(db: Session, gasto_fijo: GastoFijo, usuario_id: int) -> Gasto:
    if not gasto_fijo.activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede aplicar un gasto fijo inactivo",
        )
    gasto = Gasto(
        concepto=f"{PREFIJO_GASTO_FIJO} {gasto_fijo.concepto} ({gasto_fijo.categoria})",
        monto=gasto_fijo.monto,
        id_usuario=usuario_id,
        fecha_gasto=datetime.now(timezone.utc),
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


def aplicar_todos_gastos_fijos(db: Session, usuario_id: int) -> list[Gasto]:
    activos = db.query(GastoFijo).filter(GastoFijo.activo.is_(True)).all()
    return [aplicar_gasto_fijo(db, gasto_fijo, usuario_id) for gasto_fijo in activos]
