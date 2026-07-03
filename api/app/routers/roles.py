from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data.db import get_db
from app.data.roles import Rol
from app.models.usuarios import RolOut
from app.security.auth import get_current_user

router = APIRouter(prefix="/api", tags=["roles"])


@router.get("/roles", response_model=list[RolOut])
def listar_roles(db: Session = Depends(get_db), _=Depends(get_current_user)) -> list[Rol]:
    return db.query(Rol).order_by(Rol.id).all()
