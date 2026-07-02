import pytest
import responses

from app.blueprints.recetas import bp as recetas_bp

BASE_URL = "http://testserver"

# base.html referencia usuarios/productos/ingredientes/recetas en el sidebar. Para
# renderizar la plantilla en aislamiento registramos tambien los blueprints hermanos
# si estan disponibles (trabajo de tasks paralelas); su ausencia no debe romper este test.
_blueprints_sidebar = [recetas_bp]
for _modulo in ("usuarios", "productos", "ingredientes"):
    try:
        _modulo_importado = __import__(f"app.blueprints.{_modulo}", fromlist=["bp"])
        _blueprints_sidebar.append(_modulo_importado.bp)
    except ImportError:
        pass


@pytest.fixture()
def client(app):
    for bp in _blueprints_sidebar:
        if bp.name not in app.blueprints:
            app.register_blueprint(bp)
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_listar_recetas_muestra_productos(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[{"id": 1, "nombre": "Latte", "categoria": {"id": 1, "nombre": "Bebidas calientes"}}],
        status=200,
    )

    respuesta = client.get("/recetas")

    assert respuesta.status_code == 200
    assert b"Latte" in respuesta.data


@responses.activate
def test_detalle_receta_muestra_ingredientes(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[{"id": 1, "nombre": "Latte", "categoria": {"id": 1, "nombre": "Bebidas calientes"}}],
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
                "ingrediente": {"id": 2, "nombre": "Leche entera", "unidad": "ml"},
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
                "stock_actual": "5000",
                "stock_minimo": "1000",
                "costo_unitario": "0.02",
                "activo": True,
            }
        ],
        status=200,
    )

    respuesta = client.get("/recetas/1")

    assert respuesta.status_code == 200
    assert b"Leche entera" in respuesta.data


@responses.activate
def test_eliminar_ingrediente_de_receta(client):
    _login_como_admin(client)
    responses.add(responses.DELETE, f"{BASE_URL}/producto_ingrediente/1/2", status=204)

    respuesta = client.post("/recetas/1/2/eliminar", follow_redirects=False)

    assert respuesta.status_code == 302
