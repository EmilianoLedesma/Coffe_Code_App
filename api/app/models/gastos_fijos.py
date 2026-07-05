from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

CATEGORIAS_GASTO_FIJO = {"Nómina", "Servicios", "Renta", "Otro"}


class GastoFijoCreate(BaseModel):
    concepto: str = Field(min_length=3, max_length=255)
    monto: Decimal = Field(gt=0)
    categoria: str = Field(min_length=2, max_length=50)


class GastoFijoUpdate(BaseModel):
    concepto: str | None = Field(default=None, min_length=3, max_length=255)
    monto: Decimal | None = Field(default=None, gt=0)
    categoria: str | None = Field(default=None, min_length=2, max_length=50)
    activo: bool | None = None


class GastoFijoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    concepto: str
    monto: Decimal
    categoria: str
    activo: bool
    fecha_creacion: datetime
    id_usuario: int


class AplicarGastoFijoOut(BaseModel):
    gasto_id: int
    concepto: str
    monto: Decimal
    fecha_gasto: datetime
