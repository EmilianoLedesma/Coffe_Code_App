from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.api_client import ApiError, login as api_login
from app.auth import api_base_url

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    correo = request.form.get("correo", "").strip()
    password = request.form.get("password", "")

    try:
        resultado = api_login(api_base_url(), correo, password)
    except ApiError as error:
        flash(error.detail, "error")
        return render_template("login.html")

    if resultado["rol"] != "Administrador":
        flash("Solo el rol Administrador puede acceder a este panel.", "error")
        return render_template("login.html")

    session.clear()
    session.permanent = True
    session["token"] = resultado["access_token"]
    session["rol"] = resultado["rol"]
    session["correo"] = correo

    return redirect(url_for("dashboard.index"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
