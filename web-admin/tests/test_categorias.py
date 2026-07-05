import importlib

import pytest
import responses

from app.blueprints.categorias import bp as categorias_bp

BASE_URL = "http://testserver"


@pytest.fixture()
def client(app):
    if "categorias" not in app.blueprints:
        app.register_blueprint(categorias_bp)
    for nombre in ("usuarios", "productos", "ingredientes", "recetas"):
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
def test_listar_categorias(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/categorias",
        json=[{"id": 1, "nombre": "Bebidas calientes", "descripcion": None, "activo": True}],
        status=200,
    )
    respuesta = client.get("/categorias")
    assert respuesta.status_code == 200
    assert b"Bebidas calientes" in respuesta.data


@responses.activate
def test_crear_categoria(client):
    _login_como_admin(client)
    responses.add(responses.GET, f"{BASE_URL}/categorias", json=[], status=200)
    responses.add(responses.POST, f"{BASE_URL}/categorias", json={"id": 2, "nombre": "Postres"}, status=201)

    respuesta = client.post(
        "/categorias/nuevo",
        data={"nombre": "Postres", "descripcion": ""},
        follow_redirects=False,
    )
    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "POST"


@responses.activate
def test_editar_categoria_desactiva(client):
    _login_como_admin(client)
    responses.add(responses.GET, f"{BASE_URL}/categorias", json=[], status=200)
    responses.add(responses.PUT, f"{BASE_URL}/categorias/1", json={"id": 1, "nombre": "Snacks"}, status=200)

    respuesta = client.post(
        "/categorias/1/editar",
        data={"nombre": "Snacks", "descripcion": "", "activo": "off"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "PUT"
