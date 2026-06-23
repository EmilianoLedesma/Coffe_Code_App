from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    apellido_paterno: str = Field(min_length=2, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)
    correo_electronico: EmailStr
    password: str = Field(min_length=8, max_length=72)
    id_rol: int


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    apellido_paterno: str | None = Field(default=None, min_length=2, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)
    correo_electronico: EmailStr | None = None
    id_rol: int | None = None
    activo: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None
    correo_electronico: str
    activo: bool
    fecha_creacion: datetime
    rol: RolOut
