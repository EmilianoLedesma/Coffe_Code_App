from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TopProductoOut(BaseModel):
    producto_id: int
    nombre: str
    cantidad_vendida: int
    ingresos: Decimal


class ReporteAdmin(BaseModel):
    desde: datetime
    hasta: datetime
    total_ventas: Decimal
    total_gastos: Decimal
    ganancia_neta: Decimal
    top_productos: list[TopProductoOut]
