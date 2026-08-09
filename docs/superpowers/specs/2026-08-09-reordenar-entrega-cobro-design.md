# Reordenar entrega y cobro — Diseño

**Fecha:** 2026-08-09
**Origen:** hallazgo en vivo durante prueba en dispositivo real de la sesión anterior. El gate de pago agregado en `2026-08-08-cierre-cuenta-tickets` bloqueaba "Marcar como Entregado" hasta cobrar — el usuario aclaró que ese no es el flujo real: Mesero entrega la comida apenas Cocina la termina (Listo→Entregado), sin depender del cobro. Recién cierra la cuenta DESPUÉS de entregar. La mesa se libera solo cuando todos sus pedidos están Entregado **y** pagados.

## Decisiones (brainstorm)

- Orden: `Listo → Entregado` (Mesero, sin gate de pago) → `Cerrar cuenta` (solo disponible en Entregado) → Caja cobra.
- `PedidosMesaScreen` deja de ocultar un pedido apenas pasa a Entregado — sigue visible hasta que está pagado.
- Backend expone un campo `ocupa_mesa: bool` en `PedidoOut`, un solo lugar de verdad reusado por la liberación de mesa y el filtro del mobile.

## Cambios

### 1. `cambiar_estado_pedido` — quitar el gate de pago en Entregado

El bloque que exige Ticket+Pago para `Entregado` (`api/app/services/pedidos.py:237-248`) se elimina — `Listo → Entregado` vuelve a ser incondicional.

### 2. `cerrar_cuenta` — precondición cambia de Listo a Entregado

`api/app/services/tickets.py::cerrar_cuenta` valida hoy `pedido.estatus.nombre != EstatusPedidoNombre.LISTO`. Cambia a `!= EstatusPedidoNombre.ENTREGADO`.

### 3. Guard de Cancelado — se elimina (código muerto)

El bloque en `cambiar_estado_pedido` que bloquea `Cancelado` si el ticket ya está pagado (`api/app/services/pedidos.py:250-261`) queda inalcanzable: `Cancelado` solo es alcanzable desde Pendiente/En preparación/Listo (nunca desde Entregado, ver `TRANSICIONES_PEDIDO_VALIDAS`), y `cerrar_cuenta` ahora exige Entregado — un pedido Cancelado nunca puede tener Ticket. Se borra el bloque y su test.

### 4. `PedidoOut.ocupa_mesa` — nuevo campo calculado

Nueva property en el modelo ORM `Pedido` (`api/app/data/pedidos.py`, mismo patrón que `Ticket.id_mesa`):

```python
@property
def ocupa_mesa(self) -> bool:
    if self.estatus.nombre == "Cancelado":
        return False
    if self.estatus.nombre == "Entregado":
        return not (self.ticket and self.ticket.pago)
    return True
```

Agregado a `PedidoOut` (`api/app/models/pedidos.py`) como `ocupa_mesa: bool`.

### 5. `_liberar_mesa_si_no_hay_pedidos_activos` — reescrita con la misma regla

En vez de filtrar por `EstatusPedido.nombre.in_(ESTATUS_PEDIDO_ACTIVOS)`, carga los pedidos de la mesa con sus tickets/pagos y cuenta cuántos tienen `ocupa_mesa == True` (misma lógica que la property, aplicada en Python ya que depende de relaciones cargadas — no hace falta traducirla a SQL, el volumen de pedidos por mesa es chico).

### 6. Mobile — `PedidosMesaScreen` filtra por `ocupa_mesa`

`getPedidosActivosDeMesa` (mobile/api/pedidos.js) deja de filtrar client-side por una lista fija de estados (`ESTADOS_ACTIVOS`) — filtra por `p.ocupa_mesa === true`, que el backend ya calculó.

### 7. Mobile — `DetalleScreen` — "Cerrar cuenta" pasa a Entregado

`puedeCerrarCuenta` cambia de `esListo` a `esEntregado`. `puedeEntregar` no cambia de condición (sigue siendo Listo + rol), solo deja de recibir el 409 del backend.

## Testing

- Backend: actualizar tests que asumían el gate de pago en Entregado (`test_entregar_sin_cerrar_cuenta_devuelve_409`, etc. — ahora deben pasar sin cobrar). Actualizar tests de `cerrar_cuenta` que asumían precondición Listo. Nuevos tests para `ocupa_mesa` y la mesa liberándose solo tras pago. Borrar el test del guard de Cancelado eliminado.
- Mobile: sin tests de componente (convención ya establecida).

## Fuera de alcance

Nada — cambio autocontenido, no toca otros hallazgos.
