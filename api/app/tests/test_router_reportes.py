from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.constants import EstatusCocinaNombre, EstatusPedidoNombre, RolNombre
from app.data.categorias import Categoria
from app.data.detalle_pedidos import DetallePedido
from app.data.ingredientes import Ingrediente
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.productos import Producto
from app.data.recetas import Receta
from app.data.tickets import Ticket
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


@pytest.fixture()
def categoria(db_session):
    cat = Categoria(nombre="Bebidas calientes", activo=True)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def producto_con_receta(db_session, categoria):
    producto = Producto(
        nombre="Latte", precio_venta=Decimal("55.00"), disponible=True, activo=True, id_categoria=categoria.id
    )
    ingrediente = Ingrediente(
        nombre="Leche entera",
        unidad="ml",
        stock_actual=Decimal("500"),
        stock_minimo=Decimal("1000"),
        costo_unitario=Decimal("0.02"),
        activo=True,
    )
    db_session.add_all([producto, ingrediente])
    db_session.flush()
    receta = Receta(id_producto=producto.id, id_ingrediente=ingrediente.id, cantidad_requerida=Decimal("200"))
    db_session.add(receta)
    db_session.flush()
    return producto, ingrediente


@pytest.fixture()
def venta_de_junio(db_session, catalogos, mesa_libre, usuario_mesero, producto_con_receta):
    producto, _ = producto_con_receta
    fecha = datetime(2026, 6, 15, tzinfo=timezone.utc)
    pedido = Pedido(
        fecha=fecha,
        id_mesa=mesa_libre.id,
        id_usuario=usuario_mesero.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.ENTREGADO].id,
    )
    db_session.add(pedido)
    db_session.flush()
    detalle = DetallePedido(
        cantidad=10,
        precio_unitario=Decimal("55.00"),
        id_producto=producto.id,
        id_pedido=pedido.id,
        id_estatus=catalogos["estatus_cocina"][EstatusCocinaNombre.LISTO].id,
    )
    db_session.add(detalle)
    db_session.flush()
    ticket = Ticket(
        subtotal=Decimal("550.00"),
        iva=Decimal("88.00"),
        total=Decimal("638.00"),
        fecha_emision=fecha,
        id_pedido=pedido.id,
        id_usuario=usuario_mesero.id,
    )
    db_session.add(ticket)
    db_session.flush()
    pago = Pago(
        monto_recibido=ticket.total,
        cambio=Decimal("0.00"),
        id_ticket=ticket.id,
        id_metodo=catalogos["metodos_pago"]["Efectivo"].id,
    )
    db_session.add(pago)
    db_session.flush()
    return ticket


def test_financiero_json_devuelve_ranking_y_margen(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get(
        "/api/reportes/financiero?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total_ventas"] == "638.00"  # Ticket.total incluye IVA (550.00 subtotal * 1.16)
    assert len(cuerpo["ranking_margen"]) == 1
    assert cuerpo["ranking_margen"][0]["nombre"] == "Latte"


def test_financiero_json_rechaza_rol_no_administrador(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.MESERO)

    respuesta = client.get(
        "/api/reportes/financiero",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_inventario_json_devuelve_riesgo(client, catalogos, producto_con_receta):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/inventario", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["riesgo"]) == 1
    assert cuerpo["riesgo"][0]["nombre"] == "Leche entera"
    assert cuerpo["riesgo"][0]["productos_afectados"] == ["Latte"]


def test_financiero_pdf_devuelve_pdf_valido(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get(
        "/api/reportes/financiero/pdf?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.content[:4] == b"%PDF"


def test_financiero_xlsx_devuelve_xlsx_valido(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get(
        "/api/reportes/financiero/xlsx?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert (
        respuesta.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert respuesta.content[:2] == b"PK"


def test_inventario_pdf_devuelve_pdf_valido(client, catalogos, producto_con_receta):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/inventario/pdf", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.content[:4] == b"%PDF"


def test_inventario_xlsx_devuelve_xlsx_valido(client, catalogos, producto_con_receta):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/inventario/xlsx", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.content[:2] == b"PK"


def test_financiero_acepta_categoria_id(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get(
        "/api/reportes/financiero?categoria_id=1", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta.status_code == 200
    assert "ventas_por_categoria" in respuesta.json()


def test_financiero_pdf_acepta_categoria_id(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get(
        "/api/reportes/financiero/pdf?categoria_id=1", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"


def test_inventario_acepta_rango_de_fechas(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get(
        "/api/reportes/inventario?desde=2026-01-01T00:00:00Z&hasta=2026-01-31T23:59:59Z",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 200
    assert "ranking_consumo" in respuesta.json()


def test_productos_json_devuelve_catalogo(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get(
        "/api/reportes/productos?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["productos"]) == 1
    assert cuerpo["productos"][0]["nombre"] == "Latte"
    assert cuerpo["productos"][0]["disponible"] is True


def test_productos_json_rechaza_rol_no_administrador(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.MESERO)

    respuesta = client.get(
        "/api/reportes/productos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_productos_pdf_devuelve_pdf_valido(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/productos/pdf", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.content[:4] == b"%PDF"


def test_productos_xlsx_devuelve_xlsx_valido(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/productos/xlsx", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert (
        respuesta.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert respuesta.content[:2] == b"PK"


def test_pedidos_json_devuelve_listado(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get(
        "/api/reportes/pedidos?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total_pedidos"] == 1
    assert len(cuerpo["pedidos"]) == 1
    assert cuerpo["pedidos"][0]["estatus"] == EstatusPedidoNombre.ENTREGADO


def test_pedidos_json_rechaza_rol_no_administrador(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.MESERO)

    respuesta = client.get(
        "/api/reportes/pedidos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_pedidos_pdf_devuelve_pdf_valido(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/pedidos/pdf", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.content[:4] == b"%PDF"


def test_pedidos_xlsx_devuelve_xlsx_valido(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/pedidos/xlsx", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert (
        respuesta.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert respuesta.content[:2] == b"PK"
