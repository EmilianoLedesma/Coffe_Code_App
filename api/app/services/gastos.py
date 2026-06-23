from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.data.gastos import Gasto
from app.data.ingredientes import Ingrediente
from app.models.ventas import CompraCreate, GastoCreate


def registrar_gasto(db: Session, datos: GastoCreate, usuario_id: int) -> Gasto:
    gasto = Gasto(concepto=datos.concepto, monto=datos.monto, id_usuario=usuario_id)
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


def registrar_compra(db: Session, datos: CompraCreate, usuario_id: int) -> tuple[Gasto, Decimal]:
    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == datos.ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingrediente no encontrado")

    gasto = Gasto(
        concepto=f"Compra de insumo: {ingrediente.nombre}",
        monto=datos.monto,
        id_usuario=usuario_id,
    )
    ingrediente.stock_actual = ingrediente.stock_actual + datos.cantidad

    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    db.refresh(ingrediente)
    return gasto, ingrediente.stock_actual
