import pytest
import responses

from app.blueprints.reportes import bp as reportes_bp

BASE_URL = "http://testserver"


@pytest.fixture()
def client(app):
    if "reportes" not in app.blueprints:
        app.register_blueprint(reportes_bp)
    for nombre_modulo, nombre_bp in [
        ("usuarios", "usuarios"),
        ("productos", "productos"),
        ("ingredientes", "ingredientes"),
        ("recetas", "recetas"),
        ("dashboard", "dashboard"),
    ]:
        try:
            modulo = __import__(f"app.blueprints.{nombre_modulo}", fromlist=["bp"])
            if nombre_bp not in app.blueprints:
                app.register_blueprint(modulo.bp)
        except ImportError:
            pass
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


def _mock_endpoints():
    reporte = {
        "desde": "2026-06-01T00:00:00",
        "hasta": "2026-06-30T00:00:00",
        "total_ventas": "1000.00",
        "total_gastos": "400.00",
        "ganancia_neta": "600.00",
        "top_productos": [
            {"producto_id": 1, "nombre": "Latte", "cantidad_vendida": 20, "ingresos": "600.00"}
        ],
    }
    responses.add(responses.GET, f"{BASE_URL}/api/reportes", json=reporte, status=200)
    responses.add(responses.GET, f"{BASE_URL}/producto_ingrediente", json=[], status=200)
    responses.add(responses.GET, f"{BASE_URL}/productos", json=[{"id": 1, "nombre": "Latte", "categoria": {"id": 1, "nombre": "Bebidas"}}], status=200)
    responses.add(
        responses.GET,
        f"{BASE_URL}/ingredientes",
        json=[{"id": 1, "nombre": "Leche", "unidad": "ml", "stock_actual": "500", "stock_minimo": "1000", "costo_unitario": "0.02", "activo": True}],
        status=200,
    )


@responses.activate
def test_exportar_pdf_devuelve_content_type_pdf(client):
    _login_como_admin(client)
    _mock_endpoints()

    respuesta = client.get("/reportes/exportar.pdf?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    assert respuesta.content_type == "application/pdf"
    assert respuesta.data[:4] == b"%PDF"


@responses.activate
def test_exportar_xlsx_devuelve_content_type_correcto(client):
    _login_como_admin(client)
    _mock_endpoints()

    respuesta = client.get("/reportes/exportar.xlsx?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    assert respuesta.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
