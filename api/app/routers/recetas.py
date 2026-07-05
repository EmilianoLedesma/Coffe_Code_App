from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.ingredientes import Ingrediente
from app.data.productos import Producto
from app.data.recetas import Receta
from app.models.productos import RecetaCreate, RecetaOut, RecetaUpdate
from app.security.auth import require_rol

router = APIRouter(prefix="/producto_ingrediente", tags=["recetas"])

_lectura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)
_escritura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)


@router.get("", response_model=list[RecetaOut])
def listar_por_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(_lectura),
) -> list[Receta]:
    return (
        db.query(Receta)
        .options(joinedload(Receta.ingrediente))
        .filter(Receta.id_producto == producto_id)
        .all()
    )


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

    receta_existente = (
        db.query(Receta)
        .filter(Receta.id_producto == datos.producto_id, Receta.id_ingrediente == datos.ingrediente_id)
        .first()
    )
    if receta_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una receta para este producto e ingrediente",
        )

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


@router.put("/{producto_id}/{ingrediente_id}", response_model=RecetaOut)
def actualizar_receta(
    producto_id: int,
    ingrediente_id: int,
    datos: RecetaUpdate,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> Receta:
    receta = (
        db.query(Receta)
        .filter(Receta.id_producto == producto_id, Receta.id_ingrediente == ingrediente_id)
        .first()
    )
    if not receta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")

    receta.cantidad_requerida = datos.cantidad
    db.commit()
    return (
        db.query(Receta)
        .options(joinedload(Receta.ingrediente))
        .filter(Receta.id_producto == producto_id, Receta.id_ingrediente == ingrediente_id)
        .first()
    )


@router.delete("/producto/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_receta_completa(
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> None:
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    db.query(Receta).filter(Receta.id_producto == producto_id).delete()
    db.commit()


@router.delete("/{producto_id}/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_receta(
    producto_id: int,
    ingrediente_id: int,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> None:
    receta = (
        db.query(Receta)
        .filter(Receta.id_producto == producto_id, Receta.id_ingrediente == ingrediente_id)
        .first()
    )
    if not receta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    db.delete(receta)
    db.commit()
