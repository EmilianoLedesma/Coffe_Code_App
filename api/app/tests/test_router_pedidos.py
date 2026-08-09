from decimal import Decimal

from app.core.constants import EstatusPedidoNombre, RolNombre
from app.data.categorias import Categoria
from app.data.mesas import Mesa
from app.data.productos import Producto
from app.security.auth import create_access_token
from app.services.pedidos import crear_pedido
from app.models.pedidos import DetallePedidoCreate, PedidoCreate


def _token(catalogos, rol: str, user_id: int = 1) -> str:
    return create_access_token(user_id=user_id, rol=catalogos["roles"][rol].nombre)


def _crear_mesa_y_producto(db_session, catalogos):
    mesa = Mesa(numero_mesa=7, capacidad=2, id_estatus=catalogos["estatus_mesas"]["Libre"].id)
    db_session.add(mesa)
    categoria = Categoria(nombre="Bebidas", activo=True)
    db_session.add(categoria)
    db_session.flush()
    producto = Producto(nombre="Espresso", precio_venta=Decimal("30.00"), disponible=True, activo=True, id_categoria=categoria.id)
    db_session.add(producto)
    db_session.flush()
    return mesa, producto


def test_listar_pedidos_filtra_por_mesa_id(client, db_session, catalogos, usuario_mesero):
    mesa_1, producto = _crear_mesa_y_producto(db_session, catalogos)
    mesa_2 = Mesa(numero_mesa=8, capacidad=2, id_estatus=catalogos["estatus_mesas"]["Libre"].id)
    db_session.add(mesa_2)
    db_session.flush()

    crear_pedido(db_session, PedidoCreate(mesa_id=mesa_1.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    crear_pedido(db_session, PedidoCreate(mesa_id=mesa_2.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))

    token = _token(catalogos, RolNombre.MESERO)
    respuesta = client.get(f"/pedidos?mesa_id={mesa_1.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    ids_mesa = {p["id_mesa"] for p in respuesta.json()}
    assert ids_mesa == {mesa_1.id}


def test_cocinero_no_puede_agregar_item(client, db_session, catalogos, usuario_mesero):
    mesa, producto = _crear_mesa_y_producto(db_session, catalogos)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.post(
        f"/pedidos/{pedido.id}/items",
        json={"id_producto": producto.id, "cantidad": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_cocinero_no_puede_actualizar_item(client, db_session, catalogos, usuario_mesero):
    mesa, producto = _crear_mesa_y_producto(db_session, catalogos)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    item_id = pedido.detalle[0].id

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.put(
        f"/pedidos/{pedido.id}/items/{item_id}",
        json={"cantidad": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_cocinero_no_puede_eliminar_item(client, db_session, catalogos, usuario_mesero):
    mesa, producto = _crear_mesa_y_producto(db_session, catalogos)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    item_id = pedido.detalle[0].id

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.delete(
        f"/pedidos/{pedido.id}/items/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_cocinero_no_puede_cerrar_cuenta(client, db_session, catalogos, usuario_mesero):
    mesa, producto = _crear_mesa_y_producto(db_session, catalogos)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))

    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.post(
        f"/pedidos/{pedido.id}/cerrar-cuenta",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403
