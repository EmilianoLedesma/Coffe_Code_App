from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.data.db import get_db
from app.models.productos import CategoriaOut
from app.security.auth import require_rol

router = APIRouter(prefix="/categorias", tags=["categorias"])

_lectura = require_rol(
    RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR
)


@router.get("", response_model=list[CategoriaOut])
def listar(db: Session = Depends(get_db), _=Depends(_lectura)) -> list[Categoria]:
    return (
        db.query(Categoria)
        .filter(Categoria.activo.is_(True))
        .order_by(Categoria.nombre)
        .all()
    )
