from app.core.constants import RolNombre
from app.data.ingredientes import Ingrediente
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


def test_listar_ingredientes_excluye_inactivos_por_default(client, db_session, catalogos):
    db_session.add_all(
        [
            Ingrediente(nombre="Leche", unidad="ml", stock_actual=500, stock_minimo=100, costo_unitario="0.02", activo=True),
            Ingrediente(nombre="Descontinuado", unidad="g", stock_actual=0, stock_minimo=0, costo_unitario="0.01", activo=False),
        ]
    )
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get("/ingredientes", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    nombres = [i["nombre"] for i in respuesta.json()]
    assert nombres == ["Leche"]


def test_obtener_ingrediente_por_id(client, db_session, catalogos):
    ingrediente = Ingrediente(nombre="Café molido", unidad="g", stock_actual=1000, stock_minimo=200, costo_unitario="0.05", activo=True)
    db_session.add(ingrediente)
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get(f"/ingredientes/{ingrediente.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Café molido"


def test_obtener_ingrediente_inexistente_404(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get("/ingredientes/9999", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 404


def test_editar_ingrediente_no_toca_stock_actual(client, db_session, catalogos):
    ingrediente = Ingrediente(nombre="Azucar", unidad="g", stock_actual=500, stock_minimo=100, costo_unitario="0.01", activo=True)
    db_session.add(ingrediente)
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.put(
        f"/ingredientes/{ingrediente.id}",
        json={"nombre": "Azúcar refinada", "costo_unitario": "0.03"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Azúcar refinada"
    assert float(cuerpo["costo_unitario"]) == 0.03
    assert float(cuerpo["stock_actual"]) == 500.0


def test_desactivar_ingrediente(client, db_session, catalogos):
    ingrediente = Ingrediente(nombre="Vainilla", unidad="ml", stock_actual=50, stock_minimo=10, costo_unitario="0.1", activo=True)
    db_session.add(ingrediente)
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.put(f"/ingredientes/{ingrediente.id}/desactivar", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False


def test_crear_ingrediente_nombre_duplicado_exacto_409(client, db_session, catalogos):
    db_session.add(Ingrediente(nombre="Leche", unidad="ml", stock_actual=500, stock_minimo=100, costo_unitario="0.02", activo=True))
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.post(
        "/ingredientes",
        json={"nombre": "Leche", "unidad": "ml", "stock_minimo": "100", "costo_unitario": "0.02"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 409


def test_crear_ingrediente_nombre_duplicado_mayusculas_y_espacios_409(client, db_session, catalogos):
    db_session.add(Ingrediente(nombre="Leche", unidad="ml", stock_actual=500, stock_minimo=100, costo_unitario="0.02", activo=True))
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.post(
        "/ingredientes",
        json={"nombre": " LECHE ", "unidad": "ml", "stock_minimo": "100", "costo_unitario": "0.02"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 409


def test_crear_ingrediente_nombre_duplicado_contra_inactivo_409(client, db_session, catalogos):
    db_session.add(Ingrediente(nombre="Leche", unidad="ml", stock_actual=0, stock_minimo=0, costo_unitario="0.02", activo=False))
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.post(
        "/ingredientes",
        json={"nombre": "Leche", "unidad": "ml", "stock_minimo": "100", "costo_unitario": "0.02"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 409


def test_actualizar_ingrediente_renombrar_a_nombre_existente_409(client, db_session, catalogos):
    db_session.add_all(
        [
            Ingrediente(nombre="Leche", unidad="ml", stock_actual=500, stock_minimo=100, costo_unitario="0.02", activo=True),
            Ingrediente(nombre="Azucar", unidad="g", stock_actual=500, stock_minimo=100, costo_unitario="0.01", activo=True),
        ]
    )
    db_session.flush()
    azucar = db_session.query(Ingrediente).filter(Ingrediente.nombre == "Azucar").first()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.put(
        f"/ingredientes/{azucar.id}",
        json={"nombre": "Leche"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 409
