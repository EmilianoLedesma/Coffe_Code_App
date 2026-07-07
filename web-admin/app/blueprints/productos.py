from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import (
    ApiError,
    actualizar_producto,
    crear_producto,
    eliminar_producto,
    listar_categorias,
    listar_productos,
)
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("productos", __name__, url_prefix="/productos")


@bp.route("")
@login_required
def listar():
    token = current_token()
    base_url = api_base_url()
    productos = listar_productos(base_url, token, incluir_inactivos=True)
    categorias = listar_categorias(base_url, token)
    return render_template("productos.html", productos=productos, categorias=categorias)


def _payload_desde_formulario() -> dict:
    return {
        "nombre": request.form["nombre"],
        "descripcion": request.form.get("descripcion") or None,
        "precio_venta": request.form["precio_venta"],
        "disponible": request.form.get("disponible") == "on",
        "id_categoria": int(request.form["id_categoria"]),
    }


@bp.route("/nuevo", methods=["POST"])
@login_required
def crear():
    try:
        crear_producto(api_base_url(), current_token(), _payload_desde_formulario())
        flash("Producto creado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo crear el producto: {error.detail}", "error")
    return redirect(url_for("productos.listar"))


@bp.route("/<int:producto_id>/editar", methods=["POST"])
@login_required
def editar(producto_id: int):
    try:
        actualizar_producto(api_base_url(), current_token(), producto_id, _payload_desde_formulario())
        flash("Producto actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar el producto: {error.detail}", "error")
    return redirect(url_for("productos.listar"))


@bp.route("/<int:producto_id>/eliminar", methods=["POST"])
@login_required
def eliminar(producto_id: int):
    try:
        resultado = eliminar_producto(api_base_url(), current_token(), producto_id)
        flash(resultado["mensaje"], "success")
    except ApiError as error:
        flash(f"No se pudo eliminar el producto: {error.detail}", "error")
    return redirect(url_for("productos.listar"))
