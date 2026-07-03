import importlib

import pytest
import responses

from app.blueprints.cortes_diarios import bp as cortes_bp

BASE_URL = "http://testserver"


@pytest.fixture()
def client(app):
    if "cortes_diarios" not in app.blueprints:
        app.register_blueprint(cortes_bp)
    for nombre in ("usuarios", "productos", "ingredientes", "recetas", "reportes", "categorias"):
        if nombre in app.blueprints:
            continue
        try:
            modulo = importlib.import_module(f"app.blueprints.{nombre}")
        except ImportError:
            continue
        app.register_blueprint(modulo.bp)
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_index_muestra_historial(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/cortes-diarios",
        json=[
            {
                "id": 1, "fecha": "2026-06-15", "total_ventas": "150.00", "total_gastos": "30.00",
                "ganancia_neta": "120.00", "num_pedidos": 2, "num_tickets": 2,
                "generado_en": "2026-06-15T23:00:00", "desglose_metodos": [],
            }
        ],
        status=200,
    )
    respuesta = client.get("/corte-diario")
    assert respuesta.status_code == 200
    assert b"150.00" in respuesta.data


@responses.activate
def test_generar_corte_de_hoy(client):
    _login_como_admin(client)
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/cortes-diarios",
        json={
            "id": 1, "fecha": "2026-07-03", "total_ventas": "0.00", "total_gastos": "0.00",
            "ganancia_neta": "0.00", "num_pedidos": 0, "num_tickets": 0,
            "generado_en": "2026-07-03T23:00:00", "desglose_metodos": [],
        },
        status=200,
    )
    respuesta = client.post("/corte-diario/generar", follow_redirects=False)
    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "POST"
