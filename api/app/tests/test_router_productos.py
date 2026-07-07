from decimal import Decimal

from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.data.productos import Producto
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


def _crear_categoria(db_session) -> Categoria:
    categoria = Categoria(nombre="Bebidas calientes", activo=True)
    db_session.add(categoria)
    db_session.flush()
    return categoria


def test_crear_producto_nombre_duplicado_exacto_409(client, db_session, catalogos):
    categoria = _crear_categoria(db_session)
    db_session.add(
        Producto(nombre="Latte", precio_venta=Decimal("55.00"), disponible=True, activo=True, id_categoria=categoria.id)
    )
    db_session.flush()

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.post(
        "/productos",
        json={"nombre": "Latte", "precio_venta": "60.00", "disponible": True, "activo": True, "id_categoria": categoria.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 409


def test_crear_producto_nombre_duplicado_mayusculas_y_espacios_409(client, db_session, catalogos):
    categoria = _crear_categoria(db_session)
    db_session.add(
        Producto(nombre="Latte", precio_venta=Decimal("55.00"), disponible=True, activo=True, id_categoria=categoria.id)
    )
    db_session.flush()

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.post(
        "/productos",
        json={"nombre": " LATTE ", "precio_venta": "60.00", "disponible": True, "activo": True, "id_categoria": categoria.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 409


def test_crear_producto_nombre_duplicado_contra_inactivo_409(client, db_session, catalogos):
    categoria = _crear_categoria(db_session)
    db_session.add(
        Producto(nombre="Latte", precio_venta=Decimal("55.00"), disponible=False, activo=False, id_categoria=categoria.id)
    )
    db_session.flush()

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.post(
        "/productos",
        json={"nombre": "Latte", "precio_venta": "60.00", "disponible": True, "activo": True, "id_categoria": categoria.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 409


def test_crear_producto_nombre_nuevo_funciona(client, db_session, catalogos):
    categoria = _crear_categoria(db_session)
    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.post(
        "/productos",
        json={"nombre": "Capuchino", "precio_venta": "45.00", "disponible": True, "activo": True, "id_categoria": categoria.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 201


def test_actualizar_producto_renombrar_a_nombre_existente_409(client, db_session, catalogos):
    categoria = _crear_categoria(db_session)
    db_session.add_all(
        [
            Producto(nombre="Latte", precio_venta=Decimal("55.00"), disponible=True, activo=True, id_categoria=categoria.id),
            Producto(nombre="Capuchino", precio_venta=Decimal("45.00"), disponible=True, activo=True, id_categoria=categoria.id),
        ]
    )
    db_session.flush()
    capuchino = db_session.query(Producto).filter(Producto.nombre == "Capuchino").first()

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.put(
        f"/productos/{capuchino.id}",
        json={"nombre": "Latte"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 409


def test_actualizar_producto_sin_cambiar_nombre_no_dispara_verificacion(client, db_session, catalogos):
    categoria = _crear_categoria(db_session)
    producto = Producto(nombre="Latte", precio_venta=Decimal("55.00"), disponible=True, activo=True, id_categoria=categoria.id)
    db_session.add(producto)
    db_session.flush()

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.put(
        f"/productos/{producto.id}",
        json={"precio_venta": "58.00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 200
    assert float(respuesta.json()["precio_venta"]) == 58.0


def test_listar_productos_oculta_inactivos_por_defecto(client, db_session, catalogos):
    categoria = _crear_categoria(db_session)
    db_session.add(
        Producto(nombre="Activo", precio_venta=Decimal("10.00"), disponible=True, activo=True, id_categoria=categoria.id)
    )
    db_session.add(
        Producto(nombre="Inactivo", precio_venta=Decimal("10.00"), disponible=False, activo=False, id_categoria=categoria.id)
    )
    db_session.flush()

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.get("/productos", headers={"Authorization": f"Bearer {token}"})
    nombres = {p["nombre"] for p in respuesta.json()}
    assert "Activo" in nombres
    assert "Inactivo" not in nombres


def test_listar_productos_incluir_inactivos_true_los_muestra(client, db_session, catalogos):
    categoria = _crear_categoria(db_session)
    db_session.add(
        Producto(nombre="Inactivo", precio_venta=Decimal("10.00"), disponible=False, activo=False, id_categoria=categoria.id)
    )
    db_session.flush()

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.get(
        "/productos", params={"incluir_inactivos": "true"}, headers={"Authorization": f"Bearer {token}"}
    )
    nombres = {p["nombre"] for p in respuesta.json()}
    assert "Inactivo" in nombres
