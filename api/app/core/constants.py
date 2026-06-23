class EstatusPedidoNombre:
    PENDIENTE = "Pendiente"
    EN_PREPARACION = "En preparación"
    LISTO = "Listo"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"


class EstatusCocinaNombre:
    PENDIENTE = "Pendiente"
    EN_PREPARACION = "En preparación"
    LISTO = "Listo"


class RolNombre:
    MESERO = "Mesero"
    CAJERO = "Cajero"
    COCINERO = "Cocinero"
    ADMINISTRADOR = "Administrador"


class EstatusMesaNombre:
    LIBRE = "Libre"
    OCUPADA = "Ocupada"
    RESERVADA = "Reservada"


class MetodoPagoNombre:
    EFECTIVO = "Efectivo"
    TARJETA_DEBITO = "Tarjeta débito"
    TARJETA_CREDITO = "Tarjeta crédito"
    TRANSFERENCIA = "Transferencia"


TRANSICIONES_PEDIDO_VALIDAS = {
    EstatusPedidoNombre.PENDIENTE: {EstatusPedidoNombre.EN_PREPARACION, EstatusPedidoNombre.CANCELADO},
    EstatusPedidoNombre.EN_PREPARACION: {EstatusPedidoNombre.LISTO, EstatusPedidoNombre.CANCELADO},
    EstatusPedidoNombre.LISTO: {EstatusPedidoNombre.ENTREGADO, EstatusPedidoNombre.CANCELADO},
    EstatusPedidoNombre.ENTREGADO: set(),
    EstatusPedidoNombre.CANCELADO: set(),
}

ESTATUS_PEDIDO_ACTIVOS = {
    EstatusPedidoNombre.PENDIENTE,
    EstatusPedidoNombre.EN_PREPARACION,
    EstatusPedidoNombre.LISTO,
}
