from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.productos import Producto
from app.models.productos import ProductoCreate, ProductoOut, ProductoUpdate
from app.security.auth import require_rol

router = APIRouter(prefix="/productos", tags=["productos"])

_lectura = require_rol(
    RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR
)
_escritura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)


def _get_producto_o_404(db: Session, producto_id: int) -> Producto:
    producto = (
        db.query(Producto)
        .options(joinedload(Producto.categoria))
        .filter(Producto.id == producto_id)
        .first()
    )
    if not producto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return producto


@router.get("", response_model=list[ProductoOut])
def listar(db: Session = Depends(get_db), _=Depends(_lectura)) -> list[Producto]:
    return db.query(Producto).options(joinedload(Producto.categoria)).order_by(Producto.nombre).all()


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear(datos: ProductoCreate, db: Session = Depends(get_db), _=Depends(_escritura)) -> Producto:
    producto = Producto(**datos.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return _get_producto_o_404(db, producto.id)


@router.put("/{producto_id}", response_model=ProductoOut)
def actualizar(
    producto_id: int,
    datos: ProductoUpdate,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> Producto:
    producto = _get_producto_o_404(db, producto_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(producto, campo, valor)
    db.commit()
    db.refresh(producto)
    return _get_producto_o_404(db, producto.id)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(producto_id: int, db: Session = Depends(get_db), _=Depends(_escritura)) -> None:
    producto = _get_producto_o_404(db, producto_id)
    producto.activo = False
    producto.disponible = False
    db.commit()
