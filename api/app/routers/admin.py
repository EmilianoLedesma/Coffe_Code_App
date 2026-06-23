from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.usuarios import Usuario
from app.models.reportes import ReporteAdmin
from app.models.usuarios import UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.security.auth import require_rol
from app.services.reportes import calcular_reporte_admin
from app.services.usuarios import actualizar_usuario, crear_usuario

router = APIRouter(prefix="/api", tags=["admin"])

_solo_admin = require_rol(RolNombre.ADMINISTRADOR)


def _get_usuario_o_404(db: Session, usuario_id: int) -> Usuario:
    usuario = (
        db.query(Usuario)
        .options(joinedload(Usuario.rol))
        .filter(Usuario.id == usuario_id)
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), _=Depends(_solo_admin)) -> list[Usuario]:
    return db.query(Usuario).options(joinedload(Usuario.rol)).order_by(Usuario.nombre).all()


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear(datos: UsuarioCreate, db: Session = Depends(get_db), _=Depends(_solo_admin)) -> Usuario:
    usuario = crear_usuario(db, datos)
    return _get_usuario_o_404(db, usuario.id)


@router.put("/usuarios/{usuario_id}", response_model=UsuarioOut)
def actualizar(
    usuario_id: int,
    datos: UsuarioUpdate,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> Usuario:
    usuario = _get_usuario_o_404(db, usuario_id)
    usuario = actualizar_usuario(db, usuario, datos)
    return _get_usuario_o_404(db, usuario.id)


@router.get("/reportes", response_model=ReporteAdmin)
def reportes(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> dict:
    hasta = hasta or datetime.now(timezone.utc)
    desde = desde or (hasta - timedelta(days=30))
    return calcular_reporte_admin(db, desde, hasta)
