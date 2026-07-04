from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import (
    ApiError,
    actualizar_ingrediente,
    ajustar_stock_ingrediente,
    crear_ingrediente,
    desactivar_ingrediente,
    listar_ingredientes,
    registrar_compra,
)
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("ingredientes", __name__, url_prefix="/ingredientes")


@bp.route("")
@login_required
def listar():
    ingredientes = listar_ingredientes(api_base_url(), current_token())
    return render_template("ingredientes.html", ingredientes=ingredientes)


@bp.route("/nuevo", methods=["POST"])
@login_required
def crear():
    payload = {
        "nombre": request.form["nombre"],
        "unidad": request.form["unidad"],
        "stock_actual": request.form.get("stock_actual") or "0",
        "stock_minimo": request.form["stock_minimo"],
        "costo_unitario": request.form["costo_unitario"],
        "activo": True,
    }
    try:
        crear_ingrediente(api_base_url(), current_token(), payload)
        flash("Ingrediente creado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo crear el ingrediente: {error.detail}", "error")
    return redirect(url_for("ingredientes.listar"))


@bp.route("/<int:ingrediente_id>/ajustar-stock", methods=["POST"])
@login_required
def ajustar_stock(ingrediente_id: int):
    cantidad = request.form["cantidad"]
    try:
        ajustar_stock_ingrediente(api_base_url(), current_token(), ingrediente_id, cantidad)
        flash("Stock actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo ajustar el stock: {error.detail}", "error")
    return redirect(url_for("ingredientes.listar"))


@bp.route("/<int:ingrediente_id>/registrar-compra", methods=["POST"])
@login_required
def comprar(ingrediente_id: int):
    cantidad = request.form["cantidad"]
    monto = request.form["monto"]
    try:
        resultado = registrar_compra(api_base_url(), current_token(), ingrediente_id, cantidad, monto)
        flash(f"Compra registrada. Nuevo stock: {resultado['nuevo_stock']}.", "success")
    except ApiError as error:
        flash(f"No se pudo registrar la compra: {error.detail}", "error")
    return redirect(url_for("ingredientes.listar"))


@bp.route("/<int:ingrediente_id>/editar", methods=["POST"])
@login_required
def editar(ingrediente_id: int):
    payload = {
        "nombre": request.form["nombre"],
        "unidad": request.form["unidad"],
        "stock_minimo": request.form["stock_minimo"],
        "costo_unitario": request.form["costo_unitario"],
    }
    try:
        actualizar_ingrediente(api_base_url(), current_token(), ingrediente_id, payload)
        flash("Ingrediente actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar el ingrediente: {error.detail}", "error")
    return redirect(url_for("ingredientes.listar"))


@bp.route("/<int:ingrediente_id>/desactivar", methods=["POST"])
@login_required
def desactivar(ingrediente_id: int):
    try:
        desactivar_ingrediente(api_base_url(), current_token(), ingrediente_id)
        flash("Ingrediente desactivado.", "success")
    except ApiError as error:
        flash(f"No se pudo desactivar el ingrediente: {error.detail}", "error")
    return redirect(url_for("ingredientes.listar"))
