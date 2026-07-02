from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal


def periodo_anterior(desde: date, hasta: date) -> tuple[date, date]:
    duracion = hasta - desde
    return desde - duracion - timedelta(days=0), desde


def _dec(valor) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def calcular_margen_pct(total_ventas, ganancia_neta) -> Decimal:
    total_ventas = _dec(total_ventas)
    ganancia_neta = _dec(ganancia_neta)
    if total_ventas == 0:
        return Decimal("0")
    return (ganancia_neta / total_ventas * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def variacion_pct(actual, anterior) -> Decimal | None:
    actual = _dec(actual)
    anterior = _dec(anterior)
    if anterior == 0:
        return None
    return ((actual - anterior) / anterior * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def costo_receta(receta: list[dict]) -> Decimal:
    total = Decimal("0")
    for item in receta:
        cantidad = _dec(item["cantidad_requerida"])
        costo_unitario = _dec(item["ingrediente"]["costo_unitario"])
        total += cantidad * costo_unitario
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ranking_margen(top_productos: list[dict], costos_por_producto: dict[int, Decimal]) -> list[dict]:
    filas = []
    for producto in top_productos:
        producto_id = producto["producto_id"]
        cantidad = int(producto["cantidad_vendida"]) or 1
        ingresos = _dec(producto["ingresos"])
        costo_unitario_total = costos_por_producto.get(producto_id, Decimal("0"))
        costo_total = costo_unitario_total * cantidad
        margen = ingresos - costo_total
        margen_pct = calcular_margen_pct(ingresos, margen)
        filas.append(
            {
                "producto_id": producto_id,
                "nombre": producto["nombre"],
                "ingresos": ingresos,
                "costo_total": costo_total,
                "margen": margen,
                "margen_pct": margen_pct,
            }
        )
    return sorted(filas, key=lambda fila: fila["margen_pct"])


def mapa_ingrediente_a_productos(
    recetas_por_producto: dict[int, list[dict]], productos_por_id: dict[int, dict]
) -> dict[int, list[str]]:
    mapa: dict[int, list[str]] = {}
    for producto_id, receta in recetas_por_producto.items():
        nombre_producto = productos_por_id[producto_id]["nombre"]
        for item in receta:
            mapa.setdefault(item["id_ingrediente"], []).append(nombre_producto)
    return mapa


def riesgo_inventario(ingredientes: list[dict], mapa: dict[int, list[str]]) -> list[dict]:
    filas = []
    for ingrediente in ingredientes:
        stock_actual = _dec(ingrediente["stock_actual"])
        stock_minimo = _dec(ingrediente["stock_minimo"])
        if stock_actual >= stock_minimo:
            continue
        falta = stock_minimo - stock_actual
        costo_unitario = _dec(ingrediente["costo_unitario"])
        filas.append(
            {
                "id": ingrediente["id"],
                "nombre": ingrediente["nombre"],
                "unidad": ingrediente["unidad"],
                "stock_actual": stock_actual,
                "stock_minimo": stock_minimo,
                "falta": falta,
                "costo_reposicion": (falta * costo_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "productos_afectados": mapa.get(ingrediente["id"], []),
            }
        )
    return sorted(filas, key=lambda fila: fila["falta"], reverse=True)
