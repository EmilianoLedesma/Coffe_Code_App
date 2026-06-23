from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.ingredientes import Ingrediente
from app.data.productos import Producto
from app.data.recetas import Receta
from app.models.productos import RecetaCreate, RecetaOut
from app.security.auth import require_rol

router = APIRouter(prefix="/producto_ingrediente", tags=["recetas"])

_escritura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)


@router.post("", response_model=RecetaOut, status_code=status.HTTP_201_CREATED)
def crear_receta(
    datos: RecetaCreate, db: Session = Depends(get_db), _=Depends(_escritura)
) -> Receta:
    producto = db.query(Producto).filter(Producto.id == datos.producto_id).first()
    if not producto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == datos.ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingrediente no encontrado")

    receta = (
        db.query(Receta)
        .filter(Receta.id_producto == datos.producto_id, Receta.id_ingrediente == datos.ingrediente_id)
        .first()
    )
    if receta:
        receta.cantidad_requerida = datos.cantidad
    else:
        receta = Receta(
            id_producto=datos.producto_id,
            id_ingrediente=datos.ingrediente_id,
            cantidad_requerida=datos.cantidad,
        )
        db.add(receta)

    db.commit()
    return (
        db.query(Receta)
        .options(joinedload(Receta.ingrediente))
        .filter(Receta.id_producto == datos.producto_id, Receta.id_ingrediente == datos.ingrediente_id)
        .first()
    )
