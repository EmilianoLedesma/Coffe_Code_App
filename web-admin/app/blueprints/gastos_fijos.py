from datetime import date, datetime, time, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import (
    ApiError,
    aplicar_gasto_fijo,
    aplicar_todos_gastos_fijos,
    actualizar_gasto_fijo,
    crear_gasto_fijo,
    eliminar_gasto_fijo,
    listar_gastos_fijos,
    obtener_reporte_financiero,
)
from app.auth import api_base_url, current_token, login_required
from app.utils import parsear_fecha, parsear_fechas_detalle

bp = Blueprint("gastos_fijos", __name__, url_prefix="/gastos-fijos")

CATEGORIAS = ["Nómina", "Servicios", "Renta", "Otro"]


@bp.route("")
@login_required
def listar():
    base_url = api_base_url()
    token = current_token()

    hoy = date.today()
    hasta = parsear_fecha(request.args.get("hasta"), hoy)
    desde = parsear_fecha(request.args.get("desde"), hoy - timedelta(days=30))

    gastos_fijos = listar_gastos_fijos(base_url, token, incluir_inactivos=True)
    financiero = obtener_reporte_financiero(
        base_url,
        token,
        datetime.combine(desde, time.min).isoformat(),
        datetime.combine(hasta, time.max).isoformat(),
    )
    detalle_gastos = financiero.get("detalle_gastos", [])
    parsear_fechas_detalle(detalle_gastos, "fecha_gasto")

    return render_template(
        "gastos_fijos.html",
        gastos_fijos=gastos_fijos,
        categorias=CATEGORIAS,
        detalle_gastos=detalle_gastos,
        desde=desde,
        hasta=hasta,
    )


@bp.route("/nuevo", methods=["POST"])
@login_required
def crear():
    payload = {
        "concepto": request.form["concepto"],
        "monto": request.form["monto"],
        "categoria": request.form["categoria"],
    }
    try:
        crear_gasto_fijo(api_base_url(), current_token(), payload)
        flash("Gasto fijo creado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo crear el gasto fijo: {error.detail}", "error")
    return redirect(url_for("gastos_fijos.listar"))


@bp.route("/<int:gasto_fijo_id>/editar", methods=["POST"])
@login_required
def editar(gasto_fijo_id: int):
    payload = {
        "concepto": request.form["concepto"],
        "monto": request.form["monto"],
        "categoria": request.form["categoria"],
        "activo": request.form.get("activo") == "on",
    }
    try:
        actualizar_gasto_fijo(api_base_url(), current_token(), gasto_fijo_id, payload)
        flash("Gasto fijo actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar el gasto fijo: {error.detail}", "error")
    return redirect(url_for("gastos_fijos.listar"))


@bp.route("/<int:gasto_fijo_id>/eliminar", methods=["POST"])
@login_required
def eliminar(gasto_fijo_id: int):
    try:
        eliminar_gasto_fijo(api_base_url(), current_token(), gasto_fijo_id)
        flash("Gasto fijo eliminado.", "success")
    except ApiError as error:
        flash(f"No se pudo eliminar el gasto fijo: {error.detail}", "error")
    return redirect(url_for("gastos_fijos.listar"))


@bp.route("/<int:gasto_fijo_id>/aplicar", methods=["POST"])
@login_required
def aplicar(gasto_fijo_id: int):
    try:
        resultado = aplicar_gasto_fijo(api_base_url(), current_token(), gasto_fijo_id)
        flash(f"Gasto registrado: {resultado['concepto']} (${resultado['monto']}).", "success")
    except ApiError as error:
        flash(f"No se pudo aplicar el gasto fijo: {error.detail}", "error")
    return redirect(url_for("gastos_fijos.listar"))


@bp.route("/aplicar-todos", methods=["POST"])
@login_required
def aplicar_todos():
    try:
        resultados = aplicar_todos_gastos_fijos(api_base_url(), current_token())
        flash(f"Se aplicaron {len(resultados)} gastos fijos al periodo actual.", "success")
    except ApiError as error:
        flash(f"No se pudieron aplicar los gastos fijos: {error.detail}", "error")
    return redirect(url_for("gastos_fijos.listar"))
