from datetime import date, datetime, timedelta

from flask import Blueprint, Response, abort, request

from app.api_client import descargar_reporte
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("reportes", __name__, url_prefix="/reportes")

_FORMATOS_VALIDOS = {"pdf", "xlsx"}


def _parsear_fecha(valor: str | None, default: date) -> date:
    if not valor:
        return default
    return datetime.strptime(valor, "%Y-%m-%d").date()


def _proxy(categoria: str, formato: str, params: dict) -> Response:
    if formato not in _FORMATOS_VALIDOS:
        abort(404)

    token = current_token()
    base_url = api_base_url()
    respuesta = descargar_reporte(base_url, token, categoria, formato, params)

    return Response(
        respuesta.content,
        mimetype=respuesta.headers.get("Content-Type", "application/octet-stream"),
        headers={
            "Content-Disposition": respuesta.headers.get(
                "Content-Disposition", f"attachment; filename=reporte_{categoria}.{formato}"
            )
        },
    )


@bp.route("/financiero/exportar.<formato>")
@login_required
def exportar_financiero(formato: str):
    hoy = date.today()
    hasta = _parsear_fecha(request.args.get("hasta"), hoy)
    desde = _parsear_fecha(request.args.get("desde"), hoy - timedelta(days=30))
    return _proxy("financiero", formato, {"desde": desde.isoformat(), "hasta": hasta.isoformat()})


@bp.route("/inventario/exportar.<formato>")
@login_required
def exportar_inventario(formato: str):
    return _proxy("inventario", formato, {})
