from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.ingredientes import Ingrediente
from app.models.ingredientes import ActualizarStock, IngredienteCreate, IngredienteOut
from app.security.auth import require_rol

router = APIRouter(prefix="/ingredientes", tags=["ingredientes"])

_lectura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)
_escritura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)


def _get_ingrediente_o_404(db: Session, ingrediente_id: int) -> Ingrediente:
    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingrediente no encontrado")
    return ingrediente


@router.get("", response_model=list[IngredienteOut])
def listar(db: Session = Depends(get_db), _=Depends(_lectura)) -> list[Ingrediente]:
    return db.query(Ingrediente).order_by(Ingrediente.nombre).all()


@router.post("", response_model=IngredienteOut, status_code=status.HTTP_201_CREATED)
def crear(datos: IngredienteCreate, db: Session = Depends(get_db), _=Depends(_escritura)) -> Ingrediente:
    ingrediente = Ingrediente(**datos.model_dump())
    db.add(ingrediente)
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


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
