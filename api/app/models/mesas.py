from pydantic import BaseModel, ConfigDict


class EstatusMesaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class MesaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_mesa: int
    capacidad: int
    activo: bool
    estatus: EstatusMesaOut
