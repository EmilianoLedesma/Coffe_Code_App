from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.data.db import get_db
from app.models.productos import CategoriaCreate, CategoriaOut, CategoriaUpdate
from app.security.auth import require_rol

router = APIRouter(prefix="/categorias", tags=["categorias"])

_lectura = require_rol(
    RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR
)
_escritura = require_rol(RolNombre.ADMINISTRADOR)


def _get_categoria_o_404(db: Session, categoria_id: int) -> Categoria:
    categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    return categoria


@router.get("", response_model=list[CategoriaOut])
def listar(db: Session = Depends(get_db), _=Depends(_lectura)) -> list[Categoria]:
    return (
        db.query(Categoria)
        .filter(Categoria.activo.is_(True))
        .order_by(Categoria.nombre)
        .all()
    )


@router.post("", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
def crear(datos: CategoriaCreate, db: Session = Depends(get_db), _=Depends(_escritura)) -> Categoria:
    categoria = Categoria(**datos.model_dump())
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.put("/{categoria_id}", response_model=CategoriaOut)
def actualizar(
    categoria_id: int,
    datos: CategoriaUpdate,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> Categoria:
    categoria = _get_categoria_o_404(db, categoria_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(categoria, campo, valor)
    db.commit()
    db.refresh(categoria)
    return categoria
