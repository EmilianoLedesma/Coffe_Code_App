from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.data.db import get_db
from app.data.mesas import Mesa
from app.models.mesas import MesaOut
from app.security.auth import require_rol

router = APIRouter(prefix="/mesas", tags=["mesas"])


@router.get("", response_model=list[MesaOut])
def listar_mesas(
    db: Session = Depends(get_db),
    _=Depends(require_rol("Mesero", "Cajero", "Cocinero", "Administrador")),
) -> list[Mesa]:
    return db.query(Mesa).options(joinedload(Mesa.estatus)).order_by(Mesa.numero_mesa).all()
