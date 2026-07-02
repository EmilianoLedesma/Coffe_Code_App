from decimal import Decimal

from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.data.ingredientes import Ingrediente
from app.data.productos import Producto
from app.data.recetas import Receta
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


def _crear_producto_con_receta(db_session):
    categoria = Categoria(nombre="Bebidas calientes", activo=True)
    db_session.add(categoria)
    db_session.flush()

    producto = Producto(
        nombre="Latte",
        precio_venta=Decimal("55.00"),
        disponible=True,
        activo=True,
        id_categoria=categoria.id,
    )
    ingrediente = Ingrediente(
        nombre="Leche entera",
        unidad="ml",
        stock_actual=Decimal("5000"),
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


def test_listar_receta_de_producto(client, db_session, catalogos):
    producto, ingrediente = _crear_producto_con_receta(db_session)
    token = _token(catalogos, RolNombre.COCINERO)

    respuesta = client.get(
        f"/producto_ingrediente?producto_id={producto.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 1
    assert cuerpo[0]["id_ingrediente"] == ingrediente.id
    assert cuerpo[0]["ingrediente"]["nombre"] == "Leche entera"


def test_eliminar_receta_existente(client, db_session, catalogos):
    producto, ingrediente = _crear_producto_con_receta(db_session)
    token = _token(catalogos, RolNombre.COCINERO)

    respuesta = client.delete(
        f"/producto_ingrediente/{producto.id}/{ingrediente.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 204

    verificacion = client.get(
        f"/producto_ingrediente?producto_id={producto.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verificacion.json() == []


def test_eliminar_receta_inexistente_da_404(client, db_session, catalogos):
    producto, ingrediente = _crear_producto_con_receta(db_session)
    token = _token(catalogos, RolNombre.COCINERO)

    respuesta = client.delete(
        f"/producto_ingrediente/{producto.id}/9999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 404
