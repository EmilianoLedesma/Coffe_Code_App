from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.constants import EstatusMesaNombre, EstatusPedidoNombre
from app.data.categorias import Categoria
from app.data.ingredientes import Ingrediente
from app.data.mesas import Mesa
from app.data.productos import Producto
from app.data.recetas import Receta
from app.models.pedidos import DetallePedidoCreate, PedidoCreate
from app.services.pedidos import cambiar_estado_pedido, crear_pedido


@pytest.fixture()
def categoria(db_session):
    cat = Categoria(nombre="Bebidas", activo=True)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def producto_sin_receta(db_session, categoria):
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
def producto_no_disponible(db_session, categoria):
    producto = Producto(
        nombre="Fuera de temporada",
        precio_venta=Decimal("50.00"),
        disponible=False,
        activo=True,
        id_categoria=categoria.id,
    )
    db_session.add(producto)
    db_session.flush()
    return producto


@pytest.fixture()
def ingrediente_leche(db_session):
    ingrediente = Ingrediente(
        nombre="Leche",
        unidad="ml",
        stock_actual=Decimal("1000.00"),
        stock_minimo=Decimal("200.00"),
        costo_unitario=Decimal("0.05"),
    )
    db_session.add(ingrediente)
    db_session.flush()
    return ingrediente


@pytest.fixture()
def producto_capuchino_con_receta(db_session, categoria, ingrediente_leche):
    producto = Producto(
        nombre="Capuchino",
        precio_venta=Decimal("45.00"),
        disponible=True,
        activo=True,
        id_categoria=categoria.id,
    )
    db_session.add(producto)
    db_session.flush()
    receta = Receta(id_producto=producto.id, id_ingrediente=ingrediente_leche.id, cantidad_requerida=Decimal("150.00"))
    db_session.add(receta)
    db_session.flush()
    return producto


def test_pedido_create_rechaza_items_vacios():
    with pytest.raises(ValidationError):
        PedidoCreate(mesa_id=1, usuario_id=1, items=[])


def test_crear_pedido_exitoso_marca_mesa_ocupada(db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta):
    datos = PedidoCreate(
        mesa_id=mesa_libre.id,
        usuario_id=usuario_mesero.id,
        items=[DetallePedidoCreate(id_producto=producto_sin_receta.id, cantidad=2)],
    )

    pedido = crear_pedido(db_session, datos)

    assert pedido.id is not None
    assert pedido.estatus.nombre == EstatusPedidoNombre.PENDIENTE
    assert len(pedido.detalle) == 1
    assert pedido.detalle[0].cantidad == 2
    assert pedido.detalle[0].precio_unitario == Decimal("35.00")

    db_session.refresh(mesa_libre)
    assert mesa_libre.estatus.nombre == EstatusMesaNombre.OCUPADA


def test_crear_pedido_mesa_inexistente_devuelve_404(db_session, catalogos, usuario_mesero, producto_sin_receta):
    datos = PedidoCreate(
        mesa_id=99999,
        usuario_id=usuario_mesero.id,
        items=[DetallePedidoCreate(id_producto=producto_sin_receta.id, cantidad=1)],
    )

    with pytest.raises(HTTPException) as exc_info:
        crear_pedido(db_session, datos)

    assert exc_info.value.status_code == 404


def test_crear_pedido_producto_no_disponible_devuelve_409(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_no_disponible
):
    datos = PedidoCreate(
        mesa_id=mesa_libre.id,
        usuario_id=usuario_mesero.id,
        items=[DetallePedidoCreate(id_producto=producto_no_disponible.id, cantidad=1)],
    )

    with pytest.raises(HTTPException) as exc_info:
        crear_pedido(db_session, datos)

    assert exc_info.value.status_code == 409


def _crear_pedido_simple(db_session, mesa, usuario, producto, cantidad=1):
    datos = PedidoCreate(
        mesa_id=mesa.id,
        usuario_id=usuario.id,
        items=[DetallePedidoCreate(id_producto=producto.id, cantidad=cantidad)],
    )
    return crear_pedido(db_session, datos)


def test_transicion_valida_pendiente_a_en_preparacion(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta
):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)

    pedido, alertas = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)

    assert pedido.estatus.nombre == EstatusPedidoNombre.EN_PREPARACION
    assert alertas == []


def test_transicion_invalida_pendiente_a_listo_devuelve_409(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta
):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)

    with pytest.raises(HTTPException) as exc_info:
        cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)

    assert exc_info.value.status_code == 409


def test_marcar_listo_descuenta_inventario_atomicamente(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_capuchino_con_receta, ingrediente_leche
):
    """Regresion del bug real encontrado en sesion anterior: el descuento
    mezclaba Decimal (stock_actual) con float (cantidad_requerida convertida),
    lo cual lanzaba TypeError al marcar un pedido como Listo."""
    pedido = _crear_pedido_simple(
        db_session, mesa_libre, usuario_mesero, producto_capuchino_con_receta, cantidad=2
    )

    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, alertas = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)

    db_session.refresh(ingrediente_leche)
    assert ingrediente_leche.stock_actual == Decimal("700.00")  # 1000 - (2 * 150)
    assert alertas == []


def test_marcar_listo_genera_alerta_si_stock_queda_bajo_minimo(
    db_session, catalogos, mesa_libre, usuario_mesero, categoria, ingrediente_leche
):
    ingrediente_leche.stock_actual = Decimal("250.00")
    ingrediente_leche.stock_minimo = Decimal("200.00")
    db_session.flush()

    producto = Producto(
        nombre="Latte Grande",
        precio_venta=Decimal("48.00"),
        disponible=True,
        activo=True,
        id_categoria=categoria.id,
    )
    db_session.add(producto)
    db_session.flush()
    db_session.add(Receta(id_producto=producto.id, id_ingrediente=ingrediente_leche.id, cantidad_requerida=Decimal("150.00")))
    db_session.flush()

    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto, cantidad=1)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, alertas = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)

    db_session.refresh(ingrediente_leche)
    assert ingrediente_leche.stock_actual == Decimal("100.00")
    assert "Leche" in alertas


def test_entregado_libera_mesa_cuando_no_hay_mas_pedidos_activos(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta
):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)

    db_session.refresh(mesa_libre)
    assert mesa_libre.estatus.nombre == EstatusMesaNombre.LIBRE


def test_entregado_no_libera_mesa_si_hay_otro_pedido_activo(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta
):
    pedido_1 = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)
    _pedido_2 = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)

    cambiar_estado_pedido(db_session, pedido_1, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido_1, EstatusPedidoNombre.LISTO)
    cambiar_estado_pedido(db_session, pedido_1, EstatusPedidoNombre.ENTREGADO)

    db_session.refresh(mesa_libre)
    assert mesa_libre.estatus.nombre == EstatusMesaNombre.OCUPADA
