from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.ingredientes import Ingrediente
from app.data.recetas import Receta
from app.models.ingredientes import (
    ActualizarStock,
    IngredienteCreate,
    IngredienteOut,
    IngredienteUpdate,
)
from app.models.productos import EliminacionOut
from app.security.auth import require_rol

router = APIRouter(prefix="/ingredientes", tags=["ingredientes"])

_lectura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)
_escritura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)


def _get_ingrediente_o_404(db: Session, ingrediente_id: int) -> Ingrediente:
    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingrediente no encontrado")
    return ingrediente


def _verificar_nombre_no_duplicado(db: Session, nombre: str, excluir_id: int | None = None) -> None:
    nombre_normalizado = nombre.strip().lower()
    consulta = db.query(Ingrediente).filter(func.lower(func.trim(Ingrediente.nombre)) == nombre_normalizado)
    if excluir_id is not None:
        consulta = consulta.filter(Ingrediente.id != excluir_id)
    if consulta.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un ingrediente con el nombre '{nombre}'",
        )


@router.get("", response_model=list[IngredienteOut])
def listar(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    _=Depends(_lectura),
) -> list[Ingrediente]:
    consulta = db.query(Ingrediente)
    if not incluir_inactivos:
        consulta = consulta.filter(Ingrediente.activo.is_(True))
    return consulta.order_by(Ingrediente.nombre).all()


@router.get("/{ingrediente_id}", response_model=IngredienteOut)
def obtener(
    ingrediente_id: int, db: Session = Depends(get_db), _=Depends(_lectura)
) -> Ingrediente:
    return _get_ingrediente_o_404(db, ingrediente_id)


@router.post("", response_model=IngredienteOut, status_code=status.HTTP_201_CREATED)
def crear(datos: IngredienteCreate, db: Session = Depends(get_db), _=Depends(_escritura)) -> Ingrediente:
    _verificar_nombre_no_duplicado(db, datos.nombre)
    ingrediente = Ingrediente(**datos.model_dump())
    db.add(ingrediente)
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


@router.put("/{ingrediente_id}", response_model=IngredienteOut)
def actualizar(
    ingrediente_id: int,
    datos: IngredienteUpdate,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> Ingrediente:
    ingrediente = _get_ingrediente_o_404(db, ingrediente_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "nombre" in cambios:
        _verificar_nombre_no_duplicado(db, cambios["nombre"], excluir_id=ingrediente_id)
    for campo, valor in cambios.items():
        setattr(ingrediente, campo, valor)
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


@router.put("/{ingrediente_id}/desactivar", response_model=IngredienteOut)
def desactivar(
    ingrediente_id: int, db: Session = Depends(get_db), _=Depends(_escritura)
) -> Ingrediente:
    ingrediente = _get_ingrediente_o_404(db, ingrediente_id)
    ingrediente.activo = False
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


@router.delete("/{ingrediente_id}", response_model=EliminacionOut)
def eliminar(
    ingrediente_id: int, db: Session = Depends(get_db), _=Depends(_escritura)
) -> EliminacionOut:
    ingrediente = _get_ingrediente_o_404(db, ingrediente_id)
    en_uso = db.query(Receta).filter(Receta.id_ingrediente == ingrediente_id).first() is not None
    if en_uso:
        ingrediente.activo = False
        db.commit()
        return EliminacionOut(
            eliminado=False,
            mensaje="El ingrediente forma parte de una o más recetas; se desactivó en lugar de eliminarse.",
        )

    db.delete(ingrediente)
    db.commit()
    return EliminacionOut(eliminado=True, mensaje="Ingrediente eliminado permanentemente.")


@router.put("/{ingrediente_id}/stock", response_model=IngredienteOut)
def actualizar_stock(
    ingrediente_id: int,
    datos: ActualizarStock,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> Ingrediente:
    ingrediente = _get_ingrediente_o_404(db, ingrediente_id)
    nuevo_stock = ingrediente.stock_actual + datos.cantidad
    if nuevo_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El ajuste dejaría el stock en negativo",
        )
    ingrediente.stock_actual = nuevo_stock
    db.commit()
    db.refresh(ingrediente)
    return ingrediente
