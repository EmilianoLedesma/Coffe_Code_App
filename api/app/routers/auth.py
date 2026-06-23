from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.data.db import get_db
from app.data.usuarios import Usuario
from app.models.auth import LoginRequest, LoginResponse
from app.security.auth import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(credenciales: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    usuario = (
        db.query(Usuario)
        .filter(Usuario.correo_electronico == credenciales.correo_electronico)
        .first()
    )
    if not usuario or not usuario.activo or not verify_password(credenciales.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    token = create_access_token(user_id=usuario.id, rol=usuario.rol.nombre)
    return LoginResponse(access_token=token, rol=usuario.rol.nombre)
