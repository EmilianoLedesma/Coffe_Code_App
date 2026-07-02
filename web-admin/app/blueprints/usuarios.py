from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import ApiError, crear_usuario, actualizar_usuario, listar_usuarios
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

ROLES_DISPONIBLES = ["Mesero", "Cajero", "Cocinero", "Administrador"]
ROL_ID_POR_NOMBRE = {"Mesero": 1, "Cajero": 2, "Cocinero": 3, "Administrador": 4}


@bp.route("")
@login_required
def listar():
    usuarios = listar_usuarios(api_base_url(), current_token())
    return render_template("usuarios.html", usuarios=usuarios, roles=ROLES_DISPONIBLES)


@bp.route("/nuevo", methods=["POST"])
@login_required
def crear():
    payload = {
        "nombre": request.form["nombre"],
        "apellido_paterno": request.form["apellido_paterno"],
        "apellido_materno": request.form.get("apellido_materno") or None,
        "correo_electronico": request.form["correo_electronico"],
        "password": request.form["password"],
        "id_rol": int(request.form["id_rol"]),
    }
    try:
        crear_usuario(api_base_url(), current_token(), payload)
        flash("Usuario creado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo crear el usuario: {error.detail}", "error")
    return redirect(url_for("usuarios.listar"))


@bp.route("/<int:usuario_id>/editar", methods=["POST"])
@login_required
def editar(usuario_id: int):
    payload = {
        "nombre": request.form["nombre"],
        "apellido_paterno": request.form["apellido_paterno"],
        "apellido_materno": request.form.get("apellido_materno") or None,
        "correo_electronico": request.form["correo_electronico"],
        "id_rol": int(request.form["id_rol"]),
        "activo": request.form.get("activo") == "on",
    }
    try:
        actualizar_usuario(api_base_url(), current_token(), usuario_id, payload)
        flash("Usuario actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar el usuario: {error.detail}", "error")
    return redirect(url_for("usuarios.listar"))
