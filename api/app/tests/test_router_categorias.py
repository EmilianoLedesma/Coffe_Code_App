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
