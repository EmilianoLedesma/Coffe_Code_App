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


class VentaDetalleItem(BaseModel):
    fecha: datetime
    pedido_id: int
    mesa: int
    mesero: str
    producto: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class GastoPorTipoItem(BaseModel):
    tipo: str
    total: Decimal


class GastoPorUsuarioItem(BaseModel):
    usuario_id: int
    nombre: str
    total: Decimal


class GastoDetalleItem(BaseModel):
    id: int
    concepto: str
    monto: Decimal
    fecha_gasto: datetime
    usuario: str


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
    detalle_ventas: list[VentaDetalleItem]
    gastos_por_tipo: list[GastoPorTipoItem]
    gastos_por_usuario: list[GastoPorUsuarioItem]
    detalle_gastos: list[GastoDetalleItem]


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


class ProductoReporteItem(BaseModel):
    producto_id: int
    nombre: str
    categoria: str
    disponible: bool
    cantidad_vendida: int
    ingresos: Decimal
    costo_total: Decimal
    margen: Decimal
    margen_pct: Decimal


class ReporteProductosOut(BaseModel):
    desde: datetime
    hasta: datetime
    productos: list[ProductoReporteItem]


class PedidoReporteItem(BaseModel):
    pedido_id: int
    fecha: datetime
    mesa: int
    mesero: str
    estatus: str
    total: Decimal


class ReportePedidosOut(BaseModel):
    desde: datetime
    hasta: datetime
    total_pedidos: int
    total_ventas: Decimal
    pedidos: list[PedidoReporteItem]
