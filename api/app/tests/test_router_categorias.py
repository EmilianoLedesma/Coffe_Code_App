from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


def test_listar_categorias_solo_activas(client, db_session, catalogos):
    db_session.add_all(
        [
            Categoria(nombre="Bebidas calientes", activo=True),
            Categoria(nombre="Descontinuada", activo=False),
        ]
    )
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get("/categorias", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    nombres = [c["nombre"] for c in respuesta.json()]
    assert nombres == ["Bebidas calientes"]


def test_listar_categorias_requiere_rol_valido(client, db_session, catalogos):
    respuesta = client.get("/categorias")
    assert respuesta.status_code == 403


def test_crear_categoria_requiere_admin(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.post(
        "/categorias",
        json={"nombre": "Postres"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 403


def test_crear_categoria_como_admin(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.post(
        "/categorias",
        json={"nombre": "Postres", "descripcion": "Panque, pay, etc."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Postres"


def test_actualizar_categoria_desactiva(client, db_session, catalogos):
    categoria = Categoria(nombre="Snacks", activo=True)
    db_session.add(categoria)
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.put(
        f"/categorias/{categoria.id}",
        json={"activo": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Snacks"

    # una vez desactivada, listar() ya no debe incluirla
    respuesta_listar = client.get("/categorias", headers={"Authorization": f"Bearer {token}"})
    assert "Snacks" not in [c["nombre"] for c in respuesta_listar.json()]


def test_actualizar_categoria_inexistente_404(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.put(
        "/categorias/9999",
        json={"nombre": "No existe"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 404
