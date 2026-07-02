import pytest
import responses

from app.blueprints.productos import bp as productos_bp

BASE_URL = "http://testserver"


def _registrar(app, import_path, nombre):
    if nombre in app.blueprints:
        return
    try:
        module = __import__(import_path, fromlist=["bp"])
    except Exception:
        return
    app.register_blueprint(module.bp)


@pytest.fixture()
def client(app):
    if "productos" not in app.blueprints:
        app.register_blueprint(productos_bp)
    # base.html referencia estos blueprints hermanos en el sidebar; los
    # registramos si ya existen para poder renderizar en aislamiento.
    _registrar(app, "app.blueprints.usuarios", "usuarios")
    _registrar(app, "app.blueprints.ingredientes", "ingredientes")
    _registrar(app, "app.blueprints.recetas", "recetas")
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_listar_productos_muestra_categoria(client):
    _login_como_admin(client)
    responses.add(responses.GET, f"{BASE_URL}/categorias", json=[{"id": 1, "nombre": "Bebidas calientes"}], status=200)
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[
            {
                "id": 1,
                "nombre": "Latte",
                "descripcion": None,
                "precio_venta": "55.00",
                "disponible": True,
                "activo": True,
                "categoria": {"id": 1, "nombre": "Bebidas calientes"},
            }
        ],
        status=200,
    )

    respuesta = client.get("/productos")

    assert respuesta.status_code == 200
    assert b"Latte" in respuesta.data
    assert b"Bebidas calientes" in respuesta.data


@responses.activate
def test_eliminar_producto_hace_soft_delete(client):
    _login_como_admin(client)
    responses.add(responses.DELETE, f"{BASE_URL}/productos/1", status=204)

    respuesta = client.post("/productos/1/eliminar", follow_redirects=False)

    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "DELETE"
