from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.constants import (
    ESTATUS_PEDIDO_ACTIVOS,
    TRANSICIONES_PEDIDO_VALIDAS,
    EstatusCocinaNombre,
    EstatusMesaNombre,
    EstatusPedidoNombre,
)
from app.data.detalle_pedidos import DetallePedido
from app.data.estatus_cocina import EstatusCocina
from app.data.estatus_mesas import EstatusMesa
from app.data.estatus_pedidos import EstatusPedido
from app.data.ingredientes import Ingrediente
from app.data.mesas import Mesa
from app.data.pedidos import Pedido
from app.data.productos import Producto
from app.models.pedidos import PedidoCreate
from app.websockets.manager import manager


def _get_estatus_pedido_por_nombre(db: Session, nombre: str) -> EstatusPedido:
    estatus = db.query(EstatusPedido).filter(EstatusPedido.nombre == nombre).first()
    if not estatus:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Catálogo de estatus de pedido incompleto: falta '{nombre}'",
        )
    return estatus


def _get_estatus_cocina_por_nombre(db: Session, nombre: str) -> EstatusCocina:
    estatus = db.query(EstatusCocina).filter(EstatusCocina.nombre == nombre).first()
    if not estatus:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Catálogo de estatus de cocina incompleto: falta '{nombre}'",
        )
    return estatus


def crear_pedido(db: Session, datos: PedidoCreate) -> Pedido:
    mesa = db.query(Mesa).filter(Mesa.id == datos.mesa_id, Mesa.activo.is_(True)).first()
    if not mesa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada o inactiva")

    estatus_pendiente = _get_estatus_pedido_por_nombre(db, EstatusPedidoNombre.PENDIENTE)
    estatus_cocina_pendiente = _get_estatus_cocina_por_nombre(db, EstatusCocinaNombre.PENDIENTE)

    productos_ids = [item.id_producto for item in datos.items]
    productos = db.query(Producto).filter(Producto.id.in_(productos_ids)).all()
    productos_por_id = {p.id: p for p in productos}

    faltantes = set(productos_ids) - productos_por_id.keys()
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto(s) no encontrado(s): {sorted(faltantes)}",
        )

    no_disponibles = [
        productos_por_id[pid].nombre for pid in productos_ids if not productos_por_id[pid].disponible
    ]
    if no_disponibles:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Producto(s) no disponible(s): {no_disponibles}",
        )

    pedido = Pedido(
        id_mesa=mesa.id,
        id_usuario=datos.usuario_id,
        id_estatus=estatus_pendiente.id,
    )
    for item in datos.items:
        producto = productos_por_id[item.id_producto]
        pedido.detalle.append(
            DetallePedido(
                id_producto=producto.id,
                cantidad=item.cantidad,
                especificaciones=item.especificaciones,
                precio_unitario=producto.precio_venta,
                id_estatus=estatus_cocina_pendiente.id,
            )
        )

    estatus_ocupada = db.query(EstatusMesa).filter(EstatusMesa.nombre == EstatusMesaNombre.OCUPADA).first()
    if estatus_ocupada:
        mesa.id_estatus = estatus_ocupada.id

    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    manager.emitir(
        "cocina",
        {"evento": "nuevo_pedido", "pedido_id": pedido.id, "mesa_id": mesa.id},
    )
    return pedido


def _descontar_inventario_por_receta(db: Session, pedido: Pedido) -> list[str]:
    alertas_stock_bajo: list[str] = []
    necesidades: dict[int, Decimal] = {}

    productos_ids = [d.id_producto for d in pedido.detalle]
    productos = (
        db.query(Producto)
        .options(joinedload(Producto.recetas))
        .filter(Producto.id.in_(productos_ids))
        .all()
    )
    productos_por_id = {p.id: p for p in productos}

    for detalle in pedido.detalle:
        producto = productos_por_id[detalle.id_producto]
        for receta in producto.recetas:
            necesidades[receta.id_ingrediente] = necesidades.get(
                receta.id_ingrediente, Decimal("0")
            ) + receta.cantidad_requerida * detalle.cantidad

    if not necesidades:
        return alertas_stock_bajo

    ingredientes = db.query(Ingrediente).filter(Ingrediente.id.in_(necesidades.keys())).all()
    for ingrediente in ingredientes:
        cantidad_necesaria = necesidades[ingrediente.id]
        ingrediente.stock_actual = ingrediente.stock_actual - cantidad_necesaria
        if ingrediente.stock_actual < ingrediente.stock_minimo:
            alertas_stock_bajo.append(ingrediente.nombre)

    return alertas_stock_bajo


def _liberar_mesa_si_no_hay_pedidos_activos(db: Session, mesa: Mesa) -> None:
    pedidos_activos = (
        db.query(Pedido)
        .join(EstatusPedido)
        .filter(Pedido.id_mesa == mesa.id, EstatusPedido.nombre.in_(ESTATUS_PEDIDO_ACTIVOS))
        .count()
    )
    if pedidos_activos == 0:
        estatus_libre = db.query(EstatusMesa).filter(EstatusMesa.nombre == EstatusMesaNombre.LIBRE).first()
        if estatus_libre:
            mesa.id_estatus = estatus_libre.id


def cambiar_estado_pedido(db: Session, pedido: Pedido, nuevo_estatus_nombre: str) -> tuple[Pedido, list[str]]:
    estatus_actual_nombre = pedido.estatus.nombre
    permitidos = TRANSICIONES_PEDIDO_VALIDAS.get(estatus_actual_nombre, set())

    if nuevo_estatus_nombre not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Transición inválida: no se puede pasar de '{estatus_actual_nombre}' "
                f"a '{nuevo_estatus_nombre}'"
            ),
        )

    nuevo_estatus = _get_estatus_pedido_por_nombre(db, nuevo_estatus_nombre)
    alertas_stock_bajo: list[str] = []

    if nuevo_estatus_nombre == EstatusPedidoNombre.LISTO:
        alertas_stock_bajo = _descontar_inventario_por_receta(db, pedido)
        estatus_cocina_listo = _get_estatus_cocina_por_nombre(db, EstatusCocinaNombre.LISTO)
        for detalle in pedido.detalle:
            detalle.id_estatus = estatus_cocina_listo.id

    pedido.id_estatus = nuevo_estatus.id

    if nuevo_estatus_nombre == EstatusPedidoNombre.ENTREGADO:
        _liberar_mesa_si_no_hay_pedidos_activos(db, pedido.mesa)

    db.commit()
    db.refresh(pedido)

    if nuevo_estatus_nombre == EstatusPedidoNombre.EN_PREPARACION:
        mensaje = {"evento": "pedido_activado", "pedido_id": pedido.id, "mesa_id": pedido.id_mesa}
        manager.emitir("mesero", mensaje)
        manager.emitir("caja", mensaje)
    elif nuevo_estatus_nombre == EstatusPedidoNombre.LISTO:
        manager.emitir(
            "mesero",
            {
                "evento": "pedido_listo",
                "pedido_id": pedido.id,
                "mesa_id": pedido.id_mesa,
                "alertas_stock_bajo": alertas_stock_bajo,
            },
        )

    return pedido, alertas_stock_bajo
