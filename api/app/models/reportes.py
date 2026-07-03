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


class RankingMargenItem(BaseModel):
    producto_id: int
    nombre: str
    ingresos: Decimal
    costo_total: Decimal
    margen: Decimal
    margen_pct: Decimal


class VentaPorCategoriaItem(BaseModel):
    categoria_id: int
    nombre: str
    total: Decimal


class VentaPorUsuarioItem(BaseModel):
    usuario_id: int
    nombre: str
    total: Decimal


class VentaPorMetodoPagoItem(BaseModel):
    metodo_pago: str
    total: Decimal


class RankingConsumoItem(BaseModel):
    ingrediente_id: int
    nombre: str
    unidad: str
    cantidad_consumida: Decimal


class ReporteFinancieroOut(BaseModel):
    desde: datetime
    hasta: datetime
    total_ventas: Decimal
    total_gastos: Decimal
    ganancia_neta: Decimal
    margen_pct: Decimal
    margen_pct_anterior: Decimal
    variacion_ventas_pct: Decimal | None
    variacion_ganancia_pct: Decimal | None
    ranking_margen: list[RankingMargenItem]
    ventas_por_categoria: list[VentaPorCategoriaItem]
    ventas_por_usuario: list[VentaPorUsuarioItem]
    ventas_por_metodo_pago: list[VentaPorMetodoPagoItem]


class RiesgoInventarioItem(BaseModel):
    id: int
    nombre: str
    unidad: str
    stock_actual: Decimal
    stock_minimo: Decimal
    falta: Decimal
    costo_reposicion: Decimal
    productos_afectados: list[str]


class ReporteInventarioOut(BaseModel):
    riesgo: list[RiesgoInventarioItem]
    ranking_consumo: list[RankingConsumoItem]
