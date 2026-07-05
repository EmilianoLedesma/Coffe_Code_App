from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.detalle_pedidos import DetallePedido
from app.data.productos import Producto
from app.data.recetas import Receta
from app.models.productos import EliminacionOut, ProductoCreate, ProductoOut, ProductoUpdate
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


def _verificar_nombre_no_duplicado(db: Session, nombre: str, excluir_id: int | None = None) -> None:
    nombre_normalizado = nombre.strip().lower()
    consulta = db.query(Producto).filter(func.lower(func.trim(Producto.nombre)) == nombre_normalizado)
    if excluir_id is not None:
        consulta = consulta.filter(Producto.id != excluir_id)
    if consulta.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto con el nombre '{nombre}'",
        )


@router.get("", response_model=list[ProductoOut])
def listar(db: Session = Depends(get_db), _=Depends(_lectura)) -> list[Producto]:
    return db.query(Producto).options(joinedload(Producto.categoria)).order_by(Producto.nombre).all()


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear(datos: ProductoCreate, db: Session = Depends(get_db), _=Depends(_escritura)) -> Producto:
    _verificar_nombre_no_duplicado(db, datos.nombre)
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
    cambios = datos.model_dump(exclude_unset=True)
    if "nombre" in cambios:
        _verificar_nombre_no_duplicado(db, cambios["nombre"], excluir_id=producto_id)
    for campo, valor in cambios.items():
        setattr(producto, campo, valor)
    db.commit()
    db.refresh(producto)
    return _get_producto_o_404(db, producto.id)


@router.delete("/{producto_id}", response_model=EliminacionOut)
def eliminar(producto_id: int, db: Session = Depends(get_db), _=Depends(_escritura)) -> EliminacionOut:
    producto = _get_producto_o_404(db, producto_id)
    tiene_historial = (
        db.query(DetallePedido).filter(DetallePedido.id_producto == producto_id).first() is not None
    )
    if tiene_historial:
        producto.activo = False
        producto.disponible = False
        db.commit()
        return EliminacionOut(
            eliminado=False,
            mensaje="El producto tiene pedidos asociados; se desactivó en lugar de eliminarse.",
        )

    db.query(Receta).filter(Receta.id_producto == producto_id).delete()
    db.delete(producto)
    db.commit()
    return EliminacionOut(eliminado=True, mensaje="Producto eliminado permanentemente.")
