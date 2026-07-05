from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import (
    ApiError,
    crear_receta,
    eliminar_receta,
    eliminar_receta_completa,
    listar_ingredientes,
    listar_productos,
    listar_receta_producto,
)
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("recetas", __name__, url_prefix="/recetas")


@bp.route("")
@login_required
def listar():
    productos = listar_productos(api_base_url(), current_token())
    return render_template("recetas.html", productos=productos, producto_seleccionado=None, receta=None, ingredientes=None)


@bp.route("/<int:producto_id>")
@login_required
def detalle(producto_id: int):
    token = current_token()
    base_url = api_base_url()
    productos = listar_productos(base_url, token)
    producto_seleccionado = next((p for p in productos if p["id"] == producto_id), None)
    receta = listar_receta_producto(base_url, token, producto_id)
    ingredientes = listar_ingredientes(base_url, token)
    return render_template(
        "recetas.html",
        productos=productos,
        producto_seleccionado=producto_seleccionado,
        receta=receta,
        ingredientes=ingredientes,
    )


@bp.route("/<int:producto_id>/agregar", methods=["POST"])
@login_required
def agregar(producto_id: int):
    payload = {
        "producto_id": producto_id,
        "ingrediente_id": int(request.form["ingrediente_id"]),
        "cantidad": request.form["cantidad"],
    }
    try:
        crear_receta(api_base_url(), current_token(), payload)
        flash("Ingrediente agregado a la receta.", "success")
    except ApiError as error:
        flash(f"No se pudo agregar el ingrediente: {error.detail}", "error")
    return redirect(url_for("recetas.detalle", producto_id=producto_id))


@bp.route("/<int:producto_id>/<int:ingrediente_id>/eliminar", methods=["POST"])
@login_required
def eliminar(producto_id: int, ingrediente_id: int):
    try:
        eliminar_receta(api_base_url(), current_token(), producto_id, ingrediente_id)
        flash("Ingrediente quitado de la receta.", "success")
    except ApiError as error:
        flash(f"No se pudo quitar el ingrediente: {error.detail}", "error")
    return redirect(url_for("recetas.detalle", producto_id=producto_id))


@bp.route("/<int:producto_id>/eliminar-todo", methods=["POST"])
@login_required
def eliminar_todo(producto_id: int):
    try:
        eliminar_receta_completa(api_base_url(), current_token(), producto_id)
        flash("Receta eliminada por completo.", "success")
    except ApiError as error:
        flash(f"No se pudo eliminar la receta: {error.detail}", "error")
    return redirect(url_for("recetas.detalle", producto_id=producto_id))
