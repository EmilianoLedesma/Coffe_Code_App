from datetime import date
from decimal import Decimal

from app.reportes import (
    calcular_margen_pct,
    costo_receta,
    mapa_ingrediente_a_productos,
    periodo_anterior,
    ranking_margen,
    riesgo_inventario,
    variacion_pct,
)


def test_periodo_anterior_mismo_numero_de_dias():
    desde = date(2026, 6, 1)
    hasta = date(2026, 6, 10)

    desde_prev, hasta_prev = periodo_anterior(desde, hasta)

    assert hasta_prev == desde
    assert (hasta - desde) == (hasta_prev - desde_prev)
    assert desde_prev == date(2026, 5, 23)


def test_calcular_margen_pct():
    resultado = calcular_margen_pct(Decimal("1000"), Decimal("250"))
    assert resultado == Decimal("25.00")


def test_calcular_margen_pct_con_ventas_cero():
    resultado = calcular_margen_pct(Decimal("0"), Decimal("0"))
    assert resultado == Decimal("0")


def test_variacion_pct_positiva():
    resultado = variacion_pct(Decimal("120"), Decimal("100"))
    assert resultado == Decimal("20.00")


def test_variacion_pct_sin_periodo_anterior():
    resultado = variacion_pct(Decimal("120"), Decimal("0"))
    assert resultado is None


def test_costo_receta_suma_cantidad_por_costo_unitario():
    receta = [
        {"cantidad_requerida": "200.00", "ingrediente": {"costo_unitario": "0.02"}},
        {"cantidad_requerida": "10.00", "ingrediente": {"costo_unitario": "1.50"}},
    ]
    assert costo_receta(receta) == Decimal("19.00")


def test_ranking_margen_ordena_de_menor_a_mayor_margen_pct():
    top_productos = [
        {"producto_id": 1, "nombre": "Latte", "ingresos": "550.00", "cantidad_vendida": 10},
        {"producto_id": 2, "nombre": "Espresso", "ingresos": "300.00", "cantidad_vendida": 10},
    ]
    costos = {1: Decimal("40.00"), 2: Decimal("5.00")}

    resultado = ranking_margen(top_productos, costos)

    assert resultado[0]["producto_id"] == 1
    assert resultado[0]["margen_pct"] < resultado[1]["margen_pct"]


def test_mapa_ingrediente_a_productos():
    recetas_por_producto = {
        1: [{"id_ingrediente": 9, "ingrediente": {"nombre": "Leche"}}],
        2: [{"id_ingrediente": 9, "ingrediente": {"nombre": "Leche"}}],
    }
    productos_por_id = {1: {"nombre": "Latte"}, 2: {"nombre": "Capuchino"}}

    resultado = mapa_ingrediente_a_productos(recetas_por_producto, productos_por_id)

    assert sorted(resultado[9]) == ["Capuchino", "Latte"]


def test_riesgo_inventario_solo_incluye_bajo_stock_minimo():
    ingredientes = [
        {"id": 1, "nombre": "Leche", "unidad": "ml", "stock_actual": "500", "stock_minimo": "1000", "costo_unitario": "0.02"},
        {"id": 2, "nombre": "Café", "unidad": "g", "stock_actual": "5000", "stock_minimo": "1000", "costo_unitario": "0.10"},
    ]
    mapa = {1: ["Latte", "Capuchino"], 2: ["Espresso"]}

    resultado = riesgo_inventario(ingredientes, mapa)

    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Leche"
    assert resultado[0]["falta"] == Decimal("500")
    assert resultado[0]["costo_reposicion"] == Decimal("10.00")
    assert resultado[0]["productos_afectados"] == ["Latte", "Capuchino"]
