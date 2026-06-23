from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.constants import EstatusPedidoNombre, MetodoPagoNombre
from app.data.categorias import Categoria
from app.data.productos import Producto
from app.models.pedidos import DetallePedidoCreate, PedidoCreate
from app.models.ventas import VentaCreate
from app.services.pedidos import crear_pedido
from app.services.ventas import registrar_venta


@pytest.fixture()
def categoria(db_session):
    cat = Categoria(nombre="Bebidas", activo=True)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def producto(db_session, categoria):
    producto = Producto(
        nombre="Cafe Americano",
        precio_venta=Decimal("35.00"),
        disponible=True,
        activo=True,
        id_categoria=categoria.id,
    )
    db_session.add(producto)
    db_session.flush()
    return producto


@pytest.fixture()
def pedido_con_dos_cafes(db_session, catalogos, mesa_libre, usuario_mesero, producto):
    datos = PedidoCreate(
        mesa_id=mesa_libre.id,
        usuario_id=usuario_mesero.id,
        items=[DetallePedidoCreate(id_producto=producto.id, cantidad=2)],
    )
    return crear_pedido(db_session, datos)


def test_registrar_venta_calcula_iva_16_porciento_y_cambio(db_session, catalogos, pedido_con_dos_cafes):
    # subtotal = 2 * 35.00 = 70.00 ; iva = 70 * 0.16 = 11.20 ; total = 81.20
    datos = VentaCreate(pedido_id=pedido_con_dos_cafes.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00"))

    ticket = registrar_venta(db_session, datos, usuario_id=pedido_con_dos_cafes.id_usuario)

    assert ticket.subtotal == Decimal("70.00")
    assert ticket.iva == Decimal("11.20")
    assert ticket.total == Decimal("81.20")
    assert ticket.pago.monto_recibido == Decimal("100.00")
    assert ticket.pago.cambio == Decimal("18.80")

    db_session.refresh(pedido_con_dos_cafes)
    assert pedido_con_dos_cafes.total == Decimal("81.20")


def test_registrar_venta_rechaza_monto_insuficiente(db_session, catalogos, pedido_con_dos_cafes):
    datos = VentaCreate(pedido_id=pedido_con_dos_cafes.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("10.00"))

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=pedido_con_dos_cafes.id_usuario)

    assert exc_info.value.status_code == 400


def test_registrar_venta_bloquea_pago_duplicado(db_session, catalogos, pedido_con_dos_cafes):
    datos = VentaCreate(pedido_id=pedido_con_dos_cafes.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00"))
    registrar_venta(db_session, datos, usuario_id=pedido_con_dos_cafes.id_usuario)

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=pedido_con_dos_cafes.id_usuario)

    assert exc_info.value.status_code == 409


def test_registrar_venta_metodo_pago_invalido_devuelve_400(db_session, catalogos, pedido_con_dos_cafes):
    datos = VentaCreate(pedido_id=pedido_con_dos_cafes.id, metodo_pago="Bitcoin", monto=Decimal("100.00"))

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=pedido_con_dos_cafes.id_usuario)

    assert exc_info.value.status_code == 400


def test_registrar_venta_pedido_sin_items_devuelve_409(db_session, catalogos, mesa_libre, usuario_mesero):
    from app.data.pedidos import Pedido

    pedido_vacio = Pedido(
        id_mesa=mesa_libre.id,
        id_usuario=usuario_mesero.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.PENDIENTE].id,
    )
    db_session.add(pedido_vacio)
    db_session.flush()

    datos = VentaCreate(pedido_id=pedido_vacio.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("10.00"))

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=usuario_mesero.id)

    assert exc_info.value.status_code == 409
