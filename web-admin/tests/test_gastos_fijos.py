import pytest
import responses

from app.blueprints.gastos_fijos import bp as gastos_fijos_bp

BASE_URL = "http://testserver"


@pytest.fixture()
def client(app):
    if "gastos_fijos" not in app.blueprints:
        app.register_blueprint(gastos_fijos_bp)
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


def _stub_api(detalle_gastos):
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/gastos-fijos",
        json=[{"id": 1, "concepto": "Renta", "monto": "8000.00", "categoria": "Renta", "activo": True}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero",
        json={"detalle_gastos": detalle_gastos},
        status=200,
    )


@responses.activate
def test_listar_muestra_gastos_reales_del_periodo(client):
    _login_como_admin(client)
    _stub_api(
        [
            {
                "id": 7,
                "concepto": "Compra de servilletas",
                "monto": "150.50",
                "fecha_gasto": "2026-06-15T14:30:00",
                "usuario": "Ana Cajera",
            }
        ]
    )

    respuesta = client.get("/gastos-fijos?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "Gastos registrados" in cuerpo
    assert "Compra de servilletas" in cuerpo
    assert "$150.50" in cuerpo
    assert "Ana Cajera" in cuerpo
    assert "15/06/2026 14:30" in cuerpo

    financiero_call = next(
        call for call in responses.calls if "/api/reportes/financiero" in call.request.url
    )
    assert "desde=2026-06-01T00%3A00%3A00" in financiero_call.request.url
    assert "hasta=2026-06-30T23%3A59%3A59.999999" in financiero_call.request.url


@responses.activate
def test_listar_sin_gastos_muestra_estado_vacio(client):
    _login_como_admin(client)
    _stub_api([])

    respuesta = client.get("/gastos-fijos")

    assert respuesta.status_code == 200
    assert "Sin gastos registrados en este periodo." in respuesta.get_data(as_text=True)
