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


@responses.activate
def test_dashboard_hasta_incluye_todo_el_dia(client):
    """Regresión: enviar 'hasta' como fecha pelada (sin hora) hace que la API
    la interprete como medianoche, excluyendo ventas del mismo día. El
    dashboard debe pedir el rango hasta el final del día (23:59:59.999999)."""
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero",
        json={
            "desde": "2026-07-03T00:00:00",
            "hasta": "2026-07-03T23:59:59.999999",
            "total_ventas": "111.36",
            "total_gastos": "0.00",
            "ganancia_neta": "111.36",
            "margen_pct": "100.00",
            "margen_pct_anterior": "0.00",
            "variacion_ventas_pct": None,
            "variacion_ganancia_pct": None,
            "ranking_margen": [],
            "ventas_por_categoria": [],
            "ventas_por_usuario": [],
            "ventas_por_metodo_pago": [],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario",
        json={"riesgo": [], "ranking_consumo": []},
        status=200,
    )

    respuesta = client.get("/?desde=2026-07-03&hasta=2026-07-03")

    assert respuesta.status_code == 200
    financiero_call = next(
        call for call in responses.calls if "/api/reportes/financiero" in call.request.url
    )
    assert "hasta=2026-07-03T23%3A59%3A59.999999" in financiero_call.request.url
    assert b"$111.36" in respuesta.data


@responses.activate
def test_dashboard_envia_rango_de_fechas_al_reporte_de_inventario(client):
    """Regresión: el dashboard calculaba desde_dt/hasta_dt para el reporte
    financiero pero llamaba a obtener_reporte_inventario sin pasarlos, por lo
    que construir_reporte_inventario siempre devolvía ranking_consumo=[]
    sin importar el consumo real ni el rango seleccionado."""
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero",
        json={
            "desde": "2026-06-01T00:00:00",
            "hasta": "2026-06-30T23:59:59.999999",
            "total_ventas": "1000.00",
            "total_gastos": "400.00",
            "ganancia_neta": "600.00",
            "margen_pct": "60.00",
            "margen_pct_anterior": "50.00",
            "variacion_ventas_pct": "10.00",
            "variacion_ganancia_pct": "20.00",
            "ranking_margen": [],
            "ventas_por_categoria": [],
            "ventas_por_usuario": [],
            "ventas_por_metodo_pago": [],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario",
        json={
            "riesgo": [],
            "ranking_consumo": [
                {"ingrediente_id": 1, "nombre": "Leche entera", "unidad": "ml", "cantidad_consumida": "5190.00"}
            ],
        },
        status=200,
    )

    respuesta = client.get("/?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    inventario_call = next(
        call for call in responses.calls if "/api/reportes/inventario" in call.request.url
    )
    assert "desde=2026-06-01T00%3A00%3A00" in inventario_call.request.url
    assert "hasta=2026-06-30T23%3A59%3A59.999999" in inventario_call.request.url
    assert b"Leche entera" in respuesta.data
    assert b"5190.00" in respuesta.data


@responses.activate
def test_dashboard_muestra_ventas_por_metodo_pago(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero",
        json={
            "desde": "2026-01-01T00:00:00", "hasta": "2026-01-31T00:00:00",
            "total_ventas": "100.00", "total_gastos": "20.00", "ganancia_neta": "80.00",
            "margen_pct": "80.00", "margen_pct_anterior": "70.00",
            "variacion_ventas_pct": None, "variacion_ganancia_pct": None,
            "ranking_margen": [],
            "ventas_por_categoria": [],
            "ventas_por_usuario": [],
            "ventas_por_metodo_pago": [{"metodo_pago": "Efectivo", "total": "100.00"}],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario",
        json={"riesgo": [], "ranking_consumo": []},
        status=200,
    )

    respuesta = client.get("/")

    assert respuesta.status_code == 200
    assert b"Efectivo" in respuesta.data
