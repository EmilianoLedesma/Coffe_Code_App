from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import ApiError, actualizar_usuario, crear_usuario, listar_roles, listar_usuarios
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@bp.route("")
@login_required
def listar():
    token = current_token()
    base_url = api_base_url()
    roles = listar_roles(base_url, token)
    usuarios = listar_usuarios(base_url, token)
    return render_template("usuarios.html", usuarios=usuarios, roles=roles)


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
    nueva_password = request.form.get("password") or ""
    if nueva_password:
        payload["password"] = nueva_password
    try:
        actualizar_usuario(api_base_url(), current_token(), usuario_id, payload)
        flash("Usuario actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar el usuario: {error.detail}", "error")
    return redirect(url_for("usuarios.listar"))
