import importlib

import pytest
import responses

from app.blueprints.ingredientes import bp as ingredientes_bp

BASE_URL = "http://testserver"


@pytest.fixture()
def client(app):
    if "ingredientes" not in app.blueprints:
        app.register_blueprint(ingredientes_bp)
    # base.html enlaza en el sidebar a blueprints construidos por tareas
    # paralelas; se registran si ya existen para que url_for resuelva.
    for nombre in ("usuarios", "productos", "recetas"):
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
def test_listar_ingredientes_marca_stock_bajo(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/ingredientes",
        json=[
            {
                "id": 1,
                "nombre": "Leche entera",
                "unidad": "ml",
                "stock_actual": "500.00",
                "stock_minimo": "1000.00",
                "costo_unitario": "0.02",
                "activo": True,
            }
        ],
        status=200,
    )

    respuesta = client.get("/ingredientes")

    assert respuesta.status_code == 200
    assert b"Leche entera" in respuesta.data
    assert b"Stock bajo" in respuesta.data


@responses.activate
def test_ajustar_stock_envia_delta_a_la_api(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/ingredientes/1/stock",
        json={"id": 1, "stock_actual": "1500.00"},
        status=200,
    )

    respuesta = client.post(
        "/ingredientes/1/ajustar-stock",
        data={"cantidad": "1000"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    import json

    cuerpo_enviado = json.loads(responses.calls[-1].request.body)
    assert cuerpo_enviado == {"cantidad": "1000"}


@responses.activate
def test_registrar_compra_envia_datos_a_la_api(client):
    _login_como_admin(client)
    responses.add(
        responses.POST,
        f"{BASE_URL}/compras",
        json={
            "gasto": {"id": 1, "concepto": "Compra de insumo: Leche entera", "monto": "250.00"},
            "ingrediente_id": 1,
            "nuevo_stock": "5500.00",
        },
        status=201,
    )

    respuesta = client.post(
        "/ingredientes/1/registrar-compra",
        data={"cantidad": "5000", "monto": "250.00"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    import json

    cuerpo_enviado = json.loads(responses.calls[-1].request.body)
    assert cuerpo_enviado == {"ingrediente_id": 1, "cantidad": "5000", "monto": "250.00"}


@responses.activate
def test_registrar_compra_ingrediente_no_encontrado(client):
    _login_como_admin(client)
    responses.add(
        responses.POST,
        f"{BASE_URL}/compras",
        json={"detail": "Ingrediente no encontrado"},
        status=404,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/ingredientes",
        json=[],
        status=200,
    )

    respuesta = client.post(
        "/ingredientes/999/registrar-compra",
        data={"cantidad": "5000", "monto": "250.00"},
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert "No se pudo registrar la compra".encode() in respuesta.data


@responses.activate
def test_editar_ingrediente(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/ingredientes/1",
        json={"id": 1, "nombre": "Leche deslactosada"},
        status=200,
    )

    respuesta = client.post(
        "/ingredientes/1/editar",
        data={"nombre": "Leche deslactosada", "unidad": "ml", "stock_minimo": "1000", "costo_unitario": "0.03"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "PUT"


@responses.activate
def test_desactivar_ingrediente(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/ingredientes/1/desactivar",
        json={"id": 1, "activo": False},
        status=200,
    )

    respuesta = client.post("/ingredientes/1/desactivar", follow_redirects=False)

    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "PUT"
    assert responses.calls[-1].request.url.endswith("/ingredientes/1/desactivar")
