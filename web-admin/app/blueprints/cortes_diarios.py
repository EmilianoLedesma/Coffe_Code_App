from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import ApiError, generar_corte_diario, listar_cortes_diarios
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("cortes_diarios", __name__, url_prefix="/corte-diario")


@bp.route("")
@login_required
def index():
    token = current_token()
    base_url = api_base_url()
    hoy = date.today()
    cortes = listar_cortes_diarios(base_url, token, (hoy - timedelta(days=30)).isoformat(), hoy.isoformat())
    return render_template("corte_diario.html", cortes=cortes)


@bp.route("/generar", methods=["POST"])
@login_required
def generar():
    fecha = request.form.get("fecha") or None
    try:
        generar_corte_diario(api_base_url(), current_token(), fecha)
        flash("Corte diario generado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo generar el corte: {error.detail}", "error")
    return redirect(url_for("cortes_diarios.index"))
