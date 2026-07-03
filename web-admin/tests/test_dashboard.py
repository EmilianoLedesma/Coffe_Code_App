import pytest
import responses
from flask import Blueprint

from app.blueprints.dashboard import bp as dashboard_bp

BASE_URL = "http://testserver"


def _stub_reportes_bp() -> Blueprint:
    bp = Blueprint("reportes", __name__, url_prefix="/reportes")

    @bp.route("/financiero/exportar.<formato>")
    def exportar_financiero(formato):
        return ""

    @bp.route("/inventario/exportar.<formato>")
    def exportar_inventario(formato):
        return ""

    return bp


@pytest.fixture()
def client(app):
    if "dashboard" not in app.blueprints:
        app.register_blueprint(dashboard_bp)
    if "reportes" not in app.blueprints:
        try:
            from app.blueprints.reportes import bp as reportes_bp
        except Exception:
            reportes_bp = _stub_reportes_bp()
        app.register_blueprint(reportes_bp)
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_dashboard_muestra_bloque_financiero_e_inventario(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero",
        json={
            "desde": "2026-06-01T00:00:00",
            "hasta": "2026-06-30T00:00:00",
            "total_ventas": "1000.00",
            "total_gastos": "400.00",
            "ganancia_neta": "600.00",
            "margen_pct": "60.00",
            "margen_pct_anterior": "50.00",
            "variacion_ventas_pct": "10.00",
            "variacion_ganancia_pct": "20.00",
            "ranking_margen": [
                {
                    "producto_id": 1,
                    "nombre": "Latte",
                    "ingresos": "550.00",
                    "costo_total": "40.00",
                    "margen": "510.00",
                    "margen_pct": "92.73",
                }
            ],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario",
        json={
            "riesgo": [
                {
                    "id": 1,
                    "nombre": "Leche entera",
                    "unidad": "ml",
                    "stock_actual": "500",
                    "stock_minimo": "1000",
                    "falta": "500",
                    "costo_reposicion": "10.00",
                    "productos_afectados": ["Latte"],
                }
            ]
        },
        status=200,
    )

    respuesta = client.get("/?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "Ganancia neta" in cuerpo
    assert "Leche entera" in cuerpo
    assert "Latte" in cuerpo


def test_dashboard_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]
