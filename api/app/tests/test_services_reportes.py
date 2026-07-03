from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.constants import EstatusCocinaNombre, EstatusPedidoNombre
from app.data.categorias import Categoria
from app.data.detalle_pedidos import DetallePedido
from app.data.ingredientes import Ingrediente
from app.data.pedidos import Pedido
from app.data.productos import Producto
from app.data.recetas import Receta
from app.data.tickets import Ticket
from app.services.reportes import (
    calcular_margen_pct,
    calcular_riesgo_inventario,
    calcular_ranking_margen,
    construir_reporte_financiero,
    construir_reporte_inventario,
    costo_receta_producto,
    periodo_anterior,
    variacion_pct,
)


@pytest.fixture()
def categoria(db_session):
    cat = Categoria(nombre="Bebidas calientes", activo=True)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def producto_con_receta(db_session, categoria):
    producto = Producto(
        nombre="Latte",
        precio_venta=Decimal("55.00"),
        disponible=True,
        activo=True,
        id_categoria=categoria.id,
    )
    ingrediente = Ingrediente(
        nombre="Leche entera",
        unidad="ml",
        stock_actual=Decimal("5000"),
        stock_minimo=Decimal("1000"),
        costo_unitario=Decimal("0.02"),
        activo=True,
    )
    db_session.add_all([producto, ingrediente])
    db_session.flush()

    receta = Receta(id_producto=producto.id, id_ingrediente=ingrediente.id, cantidad_requerida=Decimal("200"))
    db_session.add(receta)
    db_session.flush()
    return producto, ingrediente


def test_costo_receta_producto_suma_cantidad_por_costo_unitario(db_session, producto_con_receta):
    producto, _ = producto_con_receta
    resultado = costo_receta_producto(db_session, producto.id)
    assert resultado == Decimal("4.00")  # 200 ml * 0.02


def test_costo_receta_producto_sin_receta_da_cero(db_session, categoria):
    producto = Producto(
        nombre="Agua embotellada",
        precio_venta=Decimal("15.00"),
        disponible=True,
        activo=True,
        id_categoria=categoria.id,
    )
    db_session.add(producto)
    db_session.flush()
    assert costo_receta_producto(db_session, producto.id) == Decimal("0")


def test_periodo_anterior_mismo_numero_de_dias():
    desde = datetime(2026, 6, 1, tzinfo=timezone.utc)
    hasta = datetime(2026, 6, 10, tzinfo=timezone.utc)
    desde_prev, hasta_prev = periodo_anterior(desde, hasta)
    assert hasta_prev == desde
    assert (hasta - desde) == (hasta_prev - desde_prev)


def test_calcular_margen_pct():
    assert calcular_margen_pct(Decimal("1000"), Decimal("250")) == Decimal("25.00")


def test_variacion_pct_sin_periodo_anterior():
    assert variacion_pct(Decimal("120"), Decimal("0")) is None


def test_calcular_riesgo_inventario_solo_incluye_bajo_stock_minimo(db_session, producto_con_receta):
    producto, ingrediente = producto_con_receta
    ingrediente.stock_actual = Decimal("500")
    db_session.flush()

    resultado = calcular_riesgo_inventario(db_session)

    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Leche entera"
    assert resultado[0]["falta"] == Decimal("500")
    assert resultado[0]["costo_reposicion"] == Decimal("10.00")
    assert resultado[0]["productos_afectados"] == ["Latte"]


def test_calcular_riesgo_inventario_vacio_si_stock_suficiente(db_session, producto_con_receta):
    resultado = calcular_riesgo_inventario(db_session)
    assert resultado == []


def _crear_venta(db_session, catalogos, mesa_libre, usuario_mesero, producto, cantidad, precio_unitario, fecha):
    pedido = Pedido(
        fecha=fecha,
        id_mesa=mesa_libre.id,
        id_usuario=usuario_mesero.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.ENTREGADO].id,
    )
    db_session.add(pedido)
    db_session.flush()

    detalle = DetallePedido(
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        id_producto=producto.id,
        id_pedido=pedido.id,
        id_estatus=catalogos["estatus_cocina"][EstatusCocinaNombre.LISTO].id,
    )
    db_session.add(detalle)
    db_session.flush()

    subtotal = precio_unitario * cantidad
    ticket = Ticket(
        subtotal=subtotal,
        iva=(subtotal * Decimal("0.16")).quantize(Decimal("0.01")),
        total=(subtotal * Decimal("1.16")).quantize(Decimal("0.01")),
        fecha_emision=fecha,
        id_pedido=pedido.id,
        id_usuario=usuario_mesero.id,
    )
    db_session.add(ticket)
    db_session.flush()
    return ticket


def test_calcular_ranking_margen(db_session, catalogos, mesa_libre, usuario_mesero, producto_con_receta):
    producto, _ = producto_con_receta
    fecha = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _crear_venta(db_session, catalogos, mesa_libre, usuario_mesero, producto, cantidad=10, precio_unitario=Decimal("55.00"), fecha=fecha)

    desde = datetime(2026, 6, 1, tzinfo=timezone.utc)
    hasta = datetime(2026, 6, 30, tzinfo=timezone.utc)
    resultado = calcular_ranking_margen(db_session, desde, hasta)

    assert len(resultado) == 1
    fila = resultado[0]
    assert fila["nombre"] == "Latte"
    assert fila["ingresos"] == Decimal("550.00")
    assert fila["costo_total"] == Decimal("40.00")  # 10 * 4.00
    assert fila["margen"] == Decimal("510.00")


def test_construir_reporte_financiero(db_session, catalogos, mesa_libre, usuario_mesero, producto_con_receta):
    producto, _ = producto_con_receta
    fecha = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _crear_venta(db_session, catalogos, mesa_libre, usuario_mesero, producto, cantidad=10, precio_unitario=Decimal("55.00"), fecha=fecha)

    desde = datetime(2026, 6, 1, tzinfo=timezone.utc)
    hasta = datetime(2026, 6, 30, tzinfo=timezone.utc)
    resultado = construir_reporte_financiero(db_session, desde, hasta)

    assert resultado["total_ventas"] == Decimal("550.00")
    assert resultado["margen_pct"] > Decimal("0")
    assert len(resultado["ranking_margen"]) == 1
    assert resultado["variacion_ventas_pct"] is None  # sin ventas en periodo anterior


def test_construir_reporte_inventario_vacio(db_session, catalogos):
    resultado = construir_reporte_inventario(db_session)
    assert resultado == {"riesgo": []}
