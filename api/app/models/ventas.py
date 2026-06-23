from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class VentaCreate(BaseModel):
    pedido_id: int
    metodo_pago: str
    monto: Decimal = Field(gt=0)


class MetodoPagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class PagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    monto_recibido: Decimal
    cambio: Decimal
    metodo: MetodoPagoOut


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subtotal: Decimal
    iva: Decimal
    total: Decimal
    fecha_emision: datetime
    id_pedido: int
    id_usuario: int
    pago: PagoOut


class GastoCreate(BaseModel):
    concepto: str = Field(min_length=3, max_length=255)
    monto: Decimal = Field(gt=0)


class GastoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    monto: Decimal
    concepto: str
    fecha_gasto: datetime
    id_usuario: int


class CompraCreate(BaseModel):
    ingrediente_id: int
    cantidad: Decimal = Field(gt=0)
    monto: Decimal = Field(gt=0)


class CompraOut(BaseModel):
    gasto: GastoOut
    ingrediente_id: int
    nuevo_stock: Decimal


class ResumenCaja(BaseModel):
    desde: datetime
    hasta: datetime
    total_ventas: Decimal
    total_gastos: Decimal
    ganancia_neta: Decimal
