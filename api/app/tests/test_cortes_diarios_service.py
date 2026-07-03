from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.core.constants import EstatusPedidoNombre, MetodoPagoNombre, RolNombre
from app.data.detalle_pedidos import DetallePedido
from app.data.gastos import Gasto
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.data.usuarios import Usuario
from app.security.auth import hash_password
from app.services.cortes_diarios import generar_o_actualizar_corte, listar_cortes, obtener_corte


@pytest.fixture()
def admin_user(db_session, catalogos):
    usuario = Usuario(
        nombre="Admin", apellido_paterno="Test", correo_electronico="admin.test@coffeecode.com",
        password_hash=hash_password("Test1234!"), id_rol=catalogos["roles"][RolNombre.ADMINISTRADOR].id,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _crear_venta(db_session, catalogos, mesa_libre, admin_user, fecha, monto, metodo):
    pedido = Pedido(
        id_mesa=mesa_libre.id, id_usuario=admin_user.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.ENTREGADO].id,
        fecha=fecha, total=monto,
    )
    db_session.add(pedido)
    db_session.flush()
    ticket = Ticket(
        subtotal=monto, iva=Decimal("0"), total=monto,
        id_pedido=pedido.id, id_usuario=admin_user.id, fecha_emision=fecha,
    )
    db_session.add(ticket)
    db_session.flush()
    pago = Pago(
        monto_recibido=monto, cambio=Decimal("0"), id_ticket=ticket.id,
        id_metodo=catalogos["metodos_pago"][metodo].id,
    )
    db_session.add(pago)
    db_session.flush()
    return pedido, ticket


def test_generar_corte_calcula_totales_del_dia(db_session, catalogos, mesa_libre, admin_user):
    dia = datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc)
    _crear_venta(db_session, catalogos, mesa_libre, admin_user, dia, Decimal("100.00"), MetodoPagoNombre.EFECTIVO)
    _crear_venta(db_session, catalogos, mesa_libre, admin_user, dia, Decimal("50.00"), MetodoPagoNombre.TARJETA_DEBITO)
    db_session.add(Gasto(monto=Decimal("30.00"), concepto="Insumos", fecha_gasto=dia, id_usuario=admin_user.id))
    db_session.flush()

    corte = generar_o_actualizar_corte(db_session, date(2026, 6, 15), admin_user.id)

    assert corte.total_ventas == Decimal("150.00")
    assert corte.total_gastos == Decimal("30.00")
    assert corte.ganancia_neta == Decimal("120.00")
    assert corte.num_tickets == 2
    montos_por_metodo = {d.metodo.nombre: d.monto for d in corte.desglose_metodos}
    assert montos_por_metodo[MetodoPagoNombre.EFECTIVO] == Decimal("100.00")
    assert montos_por_metodo[MetodoPagoNombre.TARJETA_DEBITO] == Decimal("50.00")


def test_generar_corte_es_upsert_no_duplica(db_session, catalogos, mesa_libre, admin_user):
    dia = datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc)
    _crear_venta(db_session, catalogos, mesa_libre, admin_user, dia, Decimal("100.00"), MetodoPagoNombre.EFECTIVO)
    db_session.flush()

    generar_o_actualizar_corte(db_session, date(2026, 6, 16), admin_user.id)

    _crear_venta(db_session, catalogos, mesa_libre, admin_user, dia, Decimal("40.00"), MetodoPagoNombre.EFECTIVO)
    db_session.flush()
    corte_regenerado = generar_o_actualizar_corte(db_session, date(2026, 6, 16), admin_user.id)

    assert corte_regenerado.total_ventas == Decimal("140.00")
    todos = listar_cortes(db_session, date(2026, 6, 16), date(2026, 6, 16))
    assert len(todos) == 1


def test_obtener_corte_inexistente_devuelve_none(db_session, catalogos):
    assert obtener_corte(db_session, date(2099, 1, 1)) is None
