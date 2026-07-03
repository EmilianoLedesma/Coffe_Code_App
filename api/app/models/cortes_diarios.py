from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DesgloseMetodoPagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    metodo_pago: str
    monto: Decimal


class CorteDiarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date
    total_ventas: Decimal
    total_gastos: Decimal
    ganancia_neta: Decimal
    num_pedidos: int
    num_tickets: int
    generado_en: datetime
    desglose_metodos: list[DesgloseMetodoPagoOut]
