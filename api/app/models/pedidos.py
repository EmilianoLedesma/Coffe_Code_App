from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DetallePedidoCreate(BaseModel):
    id_producto: int
    cantidad: int = Field(ge=1)
    especificaciones: str | None = None


class PedidoCreate(BaseModel):
    mesa_id: int
    usuario_id: int
    items: list[DetallePedidoCreate]

    @field_validator("items")
    @classmethod
    def items_no_vacios(cls, v: list[DetallePedidoCreate]) -> list[DetallePedidoCreate]:
        if not v:
            raise ValueError("El pedido debe tener al menos un ítem")
        return v


class EstatusCocinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class ProductoResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class DetallePedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cantidad: int
    especificaciones: str | None
    precio_unitario: Decimal
    producto: ProductoResumenOut
    estatus: EstatusCocinaOut


class EstatusPedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class PedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: datetime
    total: Decimal | None
    id_mesa: int
    id_usuario: int
    estatus: EstatusPedidoOut
    detalle: list[DetallePedidoOut]


class CambioEstadoPedido(BaseModel):
    estatus: str
