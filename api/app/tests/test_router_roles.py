from app.core.constants import RolNombre
from app.security.auth import create_access_token


def test_listar_roles(client, db_session, catalogos):
    token = create_access_token(user_id=1, rol=RolNombre.MESERO)
    respuesta = client.get("/api/roles", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    nombres = {r["nombre"] for r in respuesta.json()}
    assert nombres == {"Mesero", "Cajero", "Cocinero", "Administrador"}


def test_listar_roles_requiere_autenticacion(client, db_session, catalogos):
    respuesta = client.get("/api/roles")
    assert respuesta.status_code == 403
