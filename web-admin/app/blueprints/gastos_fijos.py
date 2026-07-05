from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import (
    ApiError,
    aplicar_gasto_fijo,
    aplicar_todos_gastos_fijos,
    actualizar_gasto_fijo,
    crear_gasto_fijo,
    eliminar_gasto_fijo,
    listar_gastos_fijos,
)
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("gastos_fijos", __name__, url_prefix="/gastos-fijos")

CATEGORIAS = ["Nómina", "Servicios", "Renta", "Otro"]


@bp.route("")
@login_required
def listar():
    gastos_fijos = listar_gastos_fijos(api_base_url(), current_token(), incluir_inactivos=True)
    return render_template("gastos_fijos.html", gastos_fijos=gastos_fijos, categorias=CATEGORIAS)


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
