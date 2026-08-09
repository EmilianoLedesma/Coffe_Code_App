from decimal import Decimal

from app.core.constants import EstatusPedidoNombre, MetodoPagoNombre, RolNombre
from app.data.categorias import Categoria
from app.data.productos import Producto
from app.data.usuarios import Usuario
from app.models.pedidos import DetallePedidoCreate, PedidoCreate
from app.models.ventas import VentaCreate
from app.security.auth import create_access_token, hash_password
from app.services.pedidos import cambiar_estado_pedido, crear_pedido
from app.services.tickets import cerrar_cuenta
from app.services.ventas import registrar_venta


def _token(user_id: int, rol: str) -> str:
    return create_access_token(user_id=user_id, rol=rol)


def _crear_producto(db_session):
    categoria = Categoria(nombre="Bebidas", activo=True)
    db_session.add(categoria)
    db_session.flush()
    producto = Producto(nombre="Espresso", precio_venta=Decimal("30.00"), disponible=True, activo=True, id_categoria=categoria.id)
    db_session.add(producto)
    db_session.flush()
    return producto


def _otro_mesero(db_session, catalogos):
    usuario = Usuario(
        nombre="Otro",
        apellido_paterno="Mesero",
        correo_electronico="otro.mesero@coffeecode.com",
        password_hash=hash_password("Test1234!"),
        id_rol=catalogos["roles"][RolNombre.MESERO].id,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def test_mesero_solo_ve_sus_propios_tickets(client, db_session, catalogos, mesa_libre, usuario_mesero):
    # Creador y quien cierra la cuenta son personas distintas en ambos pedidos
    # (cruzados), para que el filtro solo pase si es por Pedido.id_usuario
    # (creador) y no por quien ejecuto cerrar_cuenta.
    producto = _crear_producto(db_session)
    otro_mesero = _otro_mesero(db_session, catalogos)

    pedido_propio = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido_propio, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido_propio, EstatusPedidoNombre.LISTO)
    pedido_propio, _ = cambiar_estado_pedido(db_session, pedido_propio, EstatusPedidoNombre.ENTREGADO)
    cerrar_cuenta(db_session, pedido_propio, usuario_id=otro_mesero.id)

    from app.data.mesas import Mesa
    mesa_2 = Mesa(numero_mesa=2, capacidad=4, id_estatus=catalogos["estatus_mesas"]["Libre"].id)
    db_session.add(mesa_2)
    db_session.flush()
    pedido_ajeno = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_2.id, usuario_id=otro_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido_ajeno, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido_ajeno, EstatusPedidoNombre.LISTO)
    pedido_ajeno, _ = cambiar_estado_pedido(db_session, pedido_ajeno, EstatusPedidoNombre.ENTREGADO)
    cerrar_cuenta(db_session, pedido_ajeno, usuario_id=usuario_mesero.id)

    token = _token(usuario_mesero.id, RolNombre.MESERO)
    respuesta = client.get("/tickets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    ids_pedido = {t["id_pedido"] for t in respuesta.json()}
    assert ids_pedido == {pedido_propio.id}


def test_cajero_ve_todos_los_tickets(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)
    cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    token = _token(999, RolNombre.CAJERO)
    respuesta = client.get("/tickets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1


def test_cajero_filtra_pagado_false_solo_ve_cuentas_abiertas(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)
    registrar_venta(db_session, VentaCreate(ticket_id=ticket.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00")), usuario_id=999)

    token = _token(999, RolNombre.CAJERO)
    respuesta = client.get("/tickets", params={"pagado": "false"}, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_cajero_filtra_pagado_true_solo_ve_cuentas_pagadas(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)

    pedido_pagado = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido_pagado, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido_pagado, EstatusPedidoNombre.LISTO)
    pedido_pagado, _ = cambiar_estado_pedido(db_session, pedido_pagado, EstatusPedidoNombre.ENTREGADO)
    ticket_pagado = cerrar_cuenta(db_session, pedido_pagado, usuario_id=usuario_mesero.id)
    registrar_venta(db_session, VentaCreate(ticket_id=ticket_pagado.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00")), usuario_id=999)

    from app.data.mesas import Mesa
    mesa_2 = Mesa(numero_mesa=2, capacidad=4, id_estatus=catalogos["estatus_mesas"]["Libre"].id)
    db_session.add(mesa_2)
    db_session.flush()
    pedido_sin_pagar = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_2.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido_sin_pagar, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido_sin_pagar, EstatusPedidoNombre.LISTO)
    pedido_sin_pagar, _ = cambiar_estado_pedido(db_session, pedido_sin_pagar, EstatusPedidoNombre.ENTREGADO)
    cerrar_cuenta(db_session, pedido_sin_pagar, usuario_id=usuario_mesero.id)

    token = _token(999, RolNombre.CAJERO)
    respuesta = client.get("/tickets", params={"pagado": "true"}, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    ids_pedido = {t["id_pedido"] for t in respuesta.json()}
    assert ids_pedido == {pedido_pagado.id}


def test_obtener_ticket_por_id_mesero_propio(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    token = _token(usuario_mesero.id, RolNombre.MESERO)
    respuesta = client.get(f"/tickets/{ticket.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == ticket.id


def test_obtener_ticket_por_id_mesero_ajeno_403(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    otro_mesero = _otro_mesero(db_session, catalogos)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=otro_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=otro_mesero.id)

    token = _token(usuario_mesero.id, RolNombre.MESERO)
    respuesta = client.get(f"/tickets/{ticket.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 403


def test_obtener_ticket_por_id_inexistente_404(client, db_session, catalogos, usuario_mesero):
    token = _token(usuario_mesero.id, RolNombre.MESERO)
    respuesta = client.get("/tickets/99999", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 404


def test_obtener_ticket_por_id_cajero_ve_cualquiera(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    token = _token(999, RolNombre.CAJERO)
    respuesta = client.get(f"/tickets/{ticket.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
