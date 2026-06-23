from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.data.roles import Rol
from app.data.usuarios import Usuario
from app.models.usuarios import UsuarioCreate, UsuarioUpdate
from app.security.auth import hash_password


def _get_rol_o_404(db: Session, id_rol: int) -> Rol:
    rol = db.query(Rol).filter(Rol.id == id_rol).first()
    if not rol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    return rol


def crear_usuario(db: Session, datos: UsuarioCreate) -> Usuario:
    existe = db.query(Usuario).filter(Usuario.correo_electronico == datos.correo_electronico).first()
    if existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario con el correo '{datos.correo_electronico}'",
        )
    _get_rol_o_404(db, datos.id_rol)

    usuario = Usuario(
        nombre=datos.nombre,
        apellido_paterno=datos.apellido_paterno,
        apellido_materno=datos.apellido_materno,
        correo_electronico=datos.correo_electronico,
        password_hash=hash_password(datos.password),
        id_rol=datos.id_rol,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_usuario(db: Session, usuario: Usuario, datos: UsuarioUpdate) -> Usuario:
    cambios = datos.model_dump(exclude_unset=True, exclude={"password"})

    if "correo_electronico" in cambios:
        duplicado = (
            db.query(Usuario)
            .filter(Usuario.correo_electronico == cambios["correo_electronico"], Usuario.id != usuario.id)
            .first()
        )
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un usuario con el correo '{cambios['correo_electronico']}'",
            )

    if "id_rol" in cambios:
        _get_rol_o_404(db, cambios["id_rol"])

    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)

    if datos.password:
        usuario.password_hash = hash_password(datos.password)

    db.commit()
    db.refresh(usuario)
    return usuario
