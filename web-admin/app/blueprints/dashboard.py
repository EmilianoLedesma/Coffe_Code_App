from datetime import date, timedelta

from flask import Blueprint, render_template, request

from app.api_client import obtener_reporte_financiero, obtener_reporte_inventario
from app.auth import api_base_url, current_token, login_required
from app.utils import parsear_fecha as _parsear_fecha

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    token = current_token()
    base_url = api_base_url()

    hoy = date.today()
    hasta = _parsear_fecha(request.args.get("hasta"), hoy)
    desde = _parsear_fecha(request.args.get("desde"), hoy - timedelta(days=30))

    financiero = obtener_reporte_financiero(base_url, token, desde.isoformat(), hasta.isoformat())
    inventario = obtener_reporte_inventario(base_url, token)

    return render_template(
        "dashboard.html",
        desde=desde,
        hasta=hasta,
        financiero=financiero,
        inventario=inventario,
    )
