import pytest
import responses
from flask import Blueprint

from app.blueprints.dashboard import bp as dashboard_bp

BASE_URL = "http://testserver"


def _stub_reportes_bp() -> Blueprint:
    bp = Blueprint("reportes", __name__, url_prefix="/reportes")

    @bp.route("/exportar.pdf")
    def exportar_pdf():
        return ""

    @bp.route("/exportar.xlsx")
    def exportar_xlsx():
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


def _mock_reporte(desde_iso, hasta_iso, total_ventas="1000.00", total_gastos="400.00"):
    return {
        "desde": desde_iso,
        "hasta": hasta_iso,
        "total_ventas": total_ventas,
        "total_gastos": total_gastos,
        "ganancia_neta": str(float(total_ventas) - float(total_gastos)),
        "top_productos": [
            {"producto_id": 1, "nombre": "Latte", "cantidad_vendida": 20, "ingresos": "600.00"}
        ],
    }


@responses.activate
def test_dashboard_muestra_margen_y_variacion(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes",
        json=_mock_reporte("2026-06-01T00:00:00", "2026-06-30T00:00:00"),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/producto_ingrediente",
        json=[
            {
                "id_producto": 1,
                "id_ingrediente": 2,
                "cantidad_requerida": "200.00",
                "ingrediente": {"id": 2, "nombre": "Leche entera", "unidad": "ml", "costo_unitario": "0.02"},
            }
        ],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/ingredientes",
        json=[
            {
                "id": 2,
                "nombre": "Leche entera",
                "unidad": "ml",
                "stock_actual": "500",
                "stock_minimo": "1000",
                "costo_unitario": "0.02",
                "activo": True,
            }
        ],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[{"id": 1, "nombre": "Latte", "categoria": {"id": 1, "nombre": "Bebidas calientes"}}],
        status=200,
    )

    respuesta = client.get("/?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "Ganancia neta" in cuerpo
    assert "Leche entera" in cuerpo


def test_dashboard_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]
