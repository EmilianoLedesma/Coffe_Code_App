from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request

from app.api_client import (
    listar_ingredientes,
    listar_productos,
    listar_receta_producto,
    obtener_reporte_admin,
)
from app.auth import api_base_url, current_token, login_required
from app.reportes import (
    calcular_margen_pct,
    costo_receta,
    mapa_ingrediente_a_productos,
    periodo_anterior,
    ranking_margen,
    riesgo_inventario,
    variacion_pct,
)

bp = Blueprint("dashboard", __name__)


def _parsear_fecha(valor: str | None, default: date) -> date:
    if not valor:
        return default
    return datetime.strptime(valor, "%Y-%m-%d").date()


@bp.route("/")
@login_required
def index():
    token = current_token()
    base_url = api_base_url()

    hoy = date.today()
    hasta = _parsear_fecha(request.args.get("hasta"), hoy)
    desde = _parsear_fecha(request.args.get("desde"), hoy - timedelta(days=30))

    reporte_actual = obtener_reporte_admin(base_url, token, desde.isoformat(), hasta.isoformat())
    desde_prev, hasta_prev = periodo_anterior(desde, hasta)
    reporte_anterior = obtener_reporte_admin(base_url, token, desde_prev.isoformat(), hasta_prev.isoformat())

    margen_actual = calcular_margen_pct(reporte_actual["total_ventas"], reporte_actual["ganancia_neta"])
    margen_anterior = calcular_margen_pct(reporte_anterior["total_ventas"], reporte_anterior["ganancia_neta"])
    variacion_ventas = variacion_pct(reporte_actual["total_ventas"], reporte_anterior["total_ventas"])
    variacion_ganancia = variacion_pct(reporte_actual["ganancia_neta"], reporte_anterior["ganancia_neta"])

    top_productos = reporte_actual["top_productos"]
    costos_por_producto = {}
    for producto in top_productos:
        receta = listar_receta_producto(base_url, token, producto["producto_id"])
        costos_por_producto[producto["producto_id"]] = costo_receta(receta) if receta else 0
    ranking = ranking_margen(top_productos, costos_por_producto)

    productos = listar_productos(base_url, token)
    productos_por_id = {p["id"]: p for p in productos}
    recetas_por_producto = {p["id"]: listar_receta_producto(base_url, token, p["id"]) for p in productos}
    mapa = mapa_ingrediente_a_productos(recetas_por_producto, productos_por_id)

    ingredientes = listar_ingredientes(base_url, token)
    riesgo = riesgo_inventario(ingredientes, mapa)

    return render_template(
        "dashboard.html",
        desde=desde,
        hasta=hasta,
        reporte=reporte_actual,
        margen_actual=margen_actual,
        margen_anterior=margen_anterior,
        variacion_ventas=variacion_ventas,
        variacion_ganancia=variacion_ganancia,
        ranking=ranking,
        riesgo=riesgo,
    )
