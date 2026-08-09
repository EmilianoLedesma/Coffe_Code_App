from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.constants import EstatusPedidoNombre, MetodoPagoNombre
from app.data.categorias import Categoria
from app.data.productos import Producto
from app.models.pedidos import DetallePedidoCreate, PedidoCreate
from app.models.ventas import VentaCreate
from app.services.pedidos import cambiar_estado_pedido, crear_pedido
from app.services.tickets import cerrar_cuenta
from app.services.ventas import registrar_venta


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


@pytest.fixture()
def ticket_cuenta_cerrada(db_session, catalogos, mesa_libre, usuario_mesero, producto):
    pedido = crear_pedido(
        db_session,
        PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=2)]),
    )
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)
    return cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)


def test_registrar_venta_calcula_cambio_y_marca_total_del_pedido(db_session, catalogos, ticket_cuenta_cerrada):
    from app.data.pedidos import Pedido

    datos = VentaCreate(ticket_id=ticket_cuenta_cerrada.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00"))

    ticket = registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    assert ticket.total == Decimal("81.20")
    assert ticket.pago.monto_recibido == Decimal("100.00")
    assert ticket.pago.cambio == Decimal("18.80")

    pedido = db_session.query(Pedido).filter(Pedido.id == ticket_cuenta_cerrada.id_pedido).first()
    assert pedido.total == Decimal("81.20")


def test_registrar_venta_rechaza_monto_insuficiente(db_session, catalogos, ticket_cuenta_cerrada):
    datos = VentaCreate(ticket_id=ticket_cuenta_cerrada.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("10.00"))

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    assert exc_info.value.status_code == 400


def test_registrar_venta_bloquea_pago_duplicado(db_session, catalogos, ticket_cuenta_cerrada):
    datos = VentaCreate(ticket_id=ticket_cuenta_cerrada.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00"))
    registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    assert exc_info.value.status_code == 409


def test_registrar_venta_metodo_pago_invalido_devuelve_400(db_session, catalogos, ticket_cuenta_cerrada):
    datos = VentaCreate(ticket_id=ticket_cuenta_cerrada.id, metodo_pago="Bitcoin", monto=Decimal("100.00"))

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    assert exc_info.value.status_code == 400


def test_registrar_venta_ticket_inexistente_devuelve_404(db_session, catalogos):
    datos = VentaCreate(ticket_id=99999, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("10.00"))

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=1)

    assert exc_info.value.status_code == 404
