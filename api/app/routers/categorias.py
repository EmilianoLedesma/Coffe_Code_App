from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.data.db import get_db
from app.data.productos import Producto
from app.models.productos import CategoriaCreate, CategoriaOut, CategoriaUpdate, EliminacionOut
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


def _verificar_nombre_no_duplicado(db: Session, nombre: str, excluir_id: int | None = None) -> None:
    nombre_normalizado = nombre.strip().lower()
    consulta = db.query(Categoria).filter(func.lower(func.trim(Categoria.nombre)) == nombre_normalizado)
    if excluir_id is not None:
        consulta = consulta.filter(Categoria.id != excluir_id)
    if consulta.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una categoría con el nombre '{nombre}'",
        )


@router.get("", response_model=list[CategoriaOut])
def listar(
    incluir_inactivas: bool = False,
    db: Session = Depends(get_db),
    _=Depends(_lectura),
) -> list[Categoria]:
    consulta = db.query(Categoria)
    if not incluir_inactivas:
        consulta = consulta.filter(Categoria.activo.is_(True))
    return consulta.order_by(Categoria.nombre).all()


@router.post("", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
def crear(datos: CategoriaCreate, db: Session = Depends(get_db), _=Depends(_escritura)) -> Categoria:
    _verificar_nombre_no_duplicado(db, datos.nombre)
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
    cambios = datos.model_dump(exclude_unset=True)
    if "nombre" in cambios:
        _verificar_nombre_no_duplicado(db, cambios["nombre"], excluir_id=categoria_id)
    for campo, valor in cambios.items():
        setattr(categoria, campo, valor)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.delete("/{categoria_id}", response_model=EliminacionOut)
def eliminar(
    categoria_id: int, db: Session = Depends(get_db), _=Depends(_escritura)
) -> EliminacionOut:
    categoria = _get_categoria_o_404(db, categoria_id)
    tiene_productos = (
        db.query(Producto).filter(Producto.id_categoria == categoria_id).first() is not None
    )
    if tiene_productos:
        categoria.activo = False
        db.commit()
        return EliminacionOut(
            eliminado=False,
            mensaje="La categoría tiene productos asociados; se desactivó en lugar de eliminarse.",
        )

    db.delete(categoria)
    db.commit()
    return EliminacionOut(eliminado=True, mensaje="Categoría eliminada permanentemente.")
