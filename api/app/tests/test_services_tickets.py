from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.constants import EstatusPedidoNombre
from app.data.categorias import Categoria
from app.data.productos import Producto
from app.models.pedidos import DetallePedidoCreate, PedidoCreate
from app.services.pedidos import cambiar_estado_pedido, crear_pedido
from app.services.tickets import cerrar_cuenta


@pytest.fixture()
def categoria(db_session):
    cat = Categoria(nombre="Bebidas", activo=True)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def producto(db_session, categoria):
    producto = Producto(nombre="Cafe Americano", precio_venta=Decimal("35.00"), disponible=True, activo=True, id_categoria=categoria.id)
    db_session.add(producto)
    db_session.flush()
    return producto


def _pedido_listo(db_session, mesa, usuario, producto, cantidad=2):
    pedido = crear_pedido(
        db_session,
        PedidoCreate(mesa_id=mesa.id, usuario_id=usuario.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=cantidad)]),
    )
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)
    return pedido


def test_cerrar_cuenta_calcula_totales_y_no_crea_pago(db_session, catalogos, mesa_libre, usuario_mesero, producto):
    pedido = _pedido_listo(db_session, mesa_libre, usuario_mesero, producto, cantidad=2)

    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    # subtotal = 2 * 35.00 = 70.00 ; iva = 70 * 0.16 = 11.20 ; total = 81.20
    assert ticket.subtotal == Decimal("70.00")
    assert ticket.iva == Decimal("11.20")
    assert ticket.total == Decimal("81.20")
    assert ticket.pago is None
    assert ticket.id_mesa == mesa_libre.id


def test_cerrar_cuenta_de_pedido_no_listo_devuelve_409(db_session, catalogos, mesa_libre, usuario_mesero, producto):
    pedido = crear_pedido(
        db_session,
        PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]),
    )

    with pytest.raises(HTTPException) as exc_info:
        cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    assert exc_info.value.status_code == 409


def test_cerrar_cuenta_dos_veces_devuelve_409(db_session, catalogos, mesa_libre, usuario_mesero, producto):
    pedido = _pedido_listo(db_session, mesa_libre, usuario_mesero, producto)
    cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    with pytest.raises(HTTPException) as exc_info:
        cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    assert exc_info.value.status_code == 409
