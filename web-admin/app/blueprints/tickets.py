from flask import Blueprint, Response, render_template, request

from app.api_client import descargar_ticket_pdf, listar_mesas, listar_tickets
from app.auth import api_base_url, current_token, login_required
from app.utils import parsear_fechas_detalle

bp = Blueprint("tickets", __name__, url_prefix="/tickets")

_FILTROS = {"si": True, "no": False}


@bp.route("")
@login_required
def listar():
    filtro = request.args.get("pagado", "")
    tickets = listar_tickets(api_base_url(), current_token(), pagado=_FILTROS.get(filtro))
    parsear_fechas_detalle(tickets, "fecha_emision")

    numero_por_mesa = {mesa["id"]: mesa["numero_mesa"] for mesa in listar_mesas(api_base_url(), current_token())}
    for ticket in tickets:
        ticket["numero_mesa"] = numero_por_mesa.get(ticket["id_mesa"], ticket["id_mesa"])

    return render_template("tickets.html", tickets=tickets, filtro=filtro)


@bp.route("/<int:ticket_id>/preview")
@login_required
def preview(ticket_id: int):
    respuesta = descargar_ticket_pdf(api_base_url(), current_token(), ticket_id)
    return Response(respuesta.content, mimetype="application/pdf")
