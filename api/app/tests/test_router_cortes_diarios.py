from datetime import date, datetime, timezone
from decimal import Decimal

from app.core.constants import EstatusPedidoNombre, MetodoPagoNombre, RolNombre
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


def test_generar_corte_requiere_admin(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.CAJERO)
    respuesta = client.post(
        "/api/cortes-diarios?fecha=2026-06-15", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta.status_code == 403


def test_generar_y_consultar_corte(client, db_session, catalogos, mesa_libre, usuario_mesero):
    dia = datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc)
    pedido = Pedido(
        id_mesa=mesa_libre.id, id_usuario=usuario_mesero.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.ENTREGADO].id,
        fecha=dia, total=Decimal("80.00"),
    )
    db_session.add(pedido)
    db_session.flush()
    ticket = Ticket(subtotal=Decimal("80.00"), iva=Decimal("0"), total=Decimal("80.00"),
                     id_pedido=pedido.id, id_usuario=usuario_mesero.id, fecha_emision=dia)
    db_session.add(ticket)
    db_session.flush()
    db_session.add(Pago(monto_recibido=Decimal("80.00"), cambio=Decimal("0"), id_ticket=ticket.id,
                         id_metodo=catalogos["metodos_pago"][MetodoPagoNombre.EFECTIVO].id))
    db_session.flush()

    token = create_access_token(user_id=usuario_mesero.id, rol=catalogos["roles"][RolNombre.ADMINISTRADOR].nombre)
    respuesta_post = client.post("/api/cortes-diarios?fecha=2026-06-15", headers={"Authorization": f"Bearer {token}"})
    assert respuesta_post.status_code == 200
    assert respuesta_post.json()["total_ventas"] == "80.00"

    respuesta_get = client.get("/api/cortes-diarios/2026-06-15", headers={"Authorization": f"Bearer {token}"})
    assert respuesta_get.status_code == 200

    respuesta_lista = client.get(
        "/api/cortes-diarios?desde=2026-06-01&hasta=2026-06-30", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta_lista.status_code == 200
    assert len(respuesta_lista.json()) == 1


def test_obtener_corte_no_generado_404(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get("/api/cortes-diarios/2099-01-01", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 404
