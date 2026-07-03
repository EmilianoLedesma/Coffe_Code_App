from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import ApiError, actualizar_categoria, crear_categoria, listar_categorias
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("categorias", __name__, url_prefix="/categorias")


@bp.route("")
@login_required
def listar():
    categorias = listar_categorias(api_base_url(), current_token())
    return render_template("categorias.html", categorias=categorias)


def _payload_desde_formulario() -> dict:
    return {
        "nombre": request.form["nombre"],
        "descripcion": request.form.get("descripcion") or None,
    }


@bp.route("/nuevo", methods=["POST"])
@login_required
def crear():
    try:
        crear_categoria(api_base_url(), current_token(), _payload_desde_formulario())
        flash("Categoría creada correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo crear la categoría: {error.detail}", "error")
    return redirect(url_for("categorias.listar"))


@bp.route("/<int:categoria_id>/editar", methods=["POST"])
@login_required
def editar(categoria_id: int):
    payload = _payload_desde_formulario()
    payload["activo"] = request.form.get("activo") == "on"
    try:
        actualizar_categoria(api_base_url(), current_token(), categoria_id, payload)
        flash("Categoría actualizada correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar la categoría: {error.detail}", "error")
    return redirect(url_for("categorias.listar"))
