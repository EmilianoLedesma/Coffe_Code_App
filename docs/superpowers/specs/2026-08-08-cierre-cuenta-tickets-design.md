# Cierre de cuenta, edición de pedidos y tickets — Diseño

**Fecha:** 2026-08-08
**Origen:** 15 hallazgos de la prueba en dispositivo real (parte 7 de la sesión 2026-08-08, ver `.superpowers/sdd/progress.md`). Este spec cubre los puntos #2, #3, #4 y #11c (base). Los demás hallazgos (#1, #5, #6, #7, #8, #9, #10, #13, #14, #15) quedan fuera de alcance, se resuelven en specs/planes separados y más chicos.

## Problema

1. **#4 — Gap de negocio real, verificado en vivo:** `Listo → Entregado` no exige pago. Se marcó un pedido Entregado sin cobrar y la mesa se liberó igual.
2. **#2 — Mesero no puede editar un pedido ya enviado.** El botón "Actualizar" en `DetalleScreen` solo refresca; no existe forma de agregar/quitar items antes de que cocina empiece a preparar.
3. **#3 — Una mesa Ocupada solo puede tener "el" pedido activo.** Tocar la mesa siempre abre el único pedido existente; no hay forma de iniciar un segundo pedido concurrente en la misma mesa. `getPedidoActivoDeMesa` puede devolver el pedido equivocado si llegara a haber más de uno.
4. **#11c — No existe ningún endpoint para leer un ticket después del momento del pago.** Bloquea cualquier futura UI de recibo/historial.

## Decisiones tomadas (brainstorm)

- **Cajero sigue cobrando** (estación fija), pero el **Mesero cierra la cuenta** como paso explícito y separado de "Entregado".
- Edición de pedido Pendiente: **agregar/quitar items libremente**, mientras el pedido siga en `Pendiente`.
- Multi-pedido por mesa: **soporte real**, cualquier momento mientras la mesa siga Ocupada — no solo tras cerrar la cuenta del anterior.
- Un Ticket por Pedido (el modelo de datos ya cerrado en `CLAUDE.md` no cambia — no se agrupan varios pedidos en un solo ticket).
- Edición de items vía **endpoints CRUD granulares** (`POST`/`PUT`/`DELETE` sobre `/pedidos/{id}/items`), no un `PUT` con diff completo.
- `GET /tickets`: Cajero/Admin ven todos, Mesero ve solo los suyos.
- **Cola de Caja solo muestra pedidos con cuenta ya cerrada** (Ticket existente sin Pago) — no cualquier pedido Listo. Fuerza el flujo Mesero-cierra → Cajero-cobra.

## Arquitectura

### Flujo de estados

```
Pendiente ──(mesero edita items)──> En preparación ──> Listo
                                                          │
                                          Mesero: POST /pedidos/{id}/cerrar-cuenta
                                          → crea Ticket (sin Pago), pedido sigue Listo
                                                          │
                                          Cajero: POST /ventas (ticket_id)
                                          → adjunta Pago al Ticket existente
                                                          │
                                          Mesero: PUT /pedidos/{id}/estado → Entregado
                                          (gate: exige Ticket con Pago)
```

`Cancelado` sigue disponible desde cualquier estado activo, sin cambios.

### 1. Edición de pedido Pendiente (backend: `api/app/routers/pedidos.py`, `api/app/services/pedidos.py`)

Nuevos endpoints, todos gateados a Mesero/Admin y a `pedido.estatus == Pendiente`:

- `POST /pedidos/{id}/items` — body `{id_producto, cantidad, especificaciones?}`. Reutiliza la validación de producto existente/disponible ya usada en `crear_pedido`.
- `PUT /pedidos/{id}/items/{item_id}` — body `{cantidad?, especificaciones?}`.
- `DELETE /pedidos/{id}/items/{item_id}` — rechaza con 409 si es el último item del pedido (mismo invariante "mínimo 1 ítem" que ya aplica al crear).

Todos devuelven 409 si `pedido.estatus != Pendiente` ("No se puede editar un pedido que ya está en preparación").

Mobile (`mobile/api/pedidos.js`, `DetalleScreen.js`): el botón "Actualizar" se reemplaza por controles reales de edición (agregar item, +/-, quitar) cuando `pedido.estatus === 'Pendiente'`; en cualquier otro estatus la pantalla vuelve a ser de solo lectura como hoy.

### 2. Multi-pedido por mesa (backend: `api/app/routers/pedidos.py`; mobile: `MesasScreen.js`)

- `GET /pedidos?mesa_id=` — nuevo query param opcional, se combina con el `estado` existente.
- `MesasScreen`: tocar una mesa Ocupada ya no intenta resolver "el" pedido activo. Navega a una lista de pedidos activos de esa mesa (`GET /pedidos?mesa_id={id}&estado=Pendiente,En preparación,Listo` — o varias llamadas si el backend no soporta estado múltiple, ver Nota) + botón "Nuevo pedido" que crea uno adicional vía el `POST /pedidos` ya existente.
- `getPedidoActivoDeMesa` se elimina; ya no aplica con soporte real de múltiples pedidos.

**Nota de implementación:** `estado` hoy es un solo valor (`EstatusPedido.nombre == estado`). Para listar "todos los activos" de una mesa hace falta soportar una lista, o el mobile hace 3 llamadas (una por estatus activo) y las junta client-side. Se decide en el plan de implementación cuál es más barato dado el código actual — no bloquea este spec.

### 3. Cerrar cuenta + gate de pago (backend: `api/app/routers/pedidos.py`, `api/app/services/pedidos.py`, `api/app/routers/caja.py`, `api/app/services/ventas.py`)

- `POST /pedidos/{id}/cerrar-cuenta` — Mesero/Admin, solo si `pedido.estatus == Listo`. Calcula `subtotal`/`iva`/`total` (misma lógica que hoy vive en `registrar_venta`, se extrae a un helper compartido) y crea un `Ticket` **sin** `Pago`. El pedido permanece en `Listo`. 409 si ya existe un Ticket para ese pedido (cuenta ya cerrada).
- `cambiar_estado_pedido`: la transición a `Entregado` ahora exige que el pedido tenga un `Ticket` con `Pago` asociado — 409 si no, con mensaje explícito ("No se puede entregar un pedido sin cobrar"). Este es el fix real del gap #4.
- `POST /ventas` cambia de contrato: en vez de crear Ticket+Pago juntos a partir de un `pedido_id`, ahora recibe el `ticket_id` de una cuenta ya cerrada y le adjunta el `Pago`. 404 si el ticket no existe, 409 si ya tiene Pago (el check ya existe, solo cambia qué dispara el 404 vs 409).
- `CajaScreen`: la cola deja de listar pedidos `Listo`, pasa a listar tickets abiertos (`GET /tickets?pagado=false` o equivalente — ver siguiente sección).

### 4. Historial de tickets (backend: nuevo router o extensión de `caja.py`)

- `GET /tickets` — filtros: `pagado` (bool, para que Caja pida solo los abiertos), `mesero_propio` (implícito por rol: si el token es Mesero, se filtra automáticamente a sus pedidos; Cajero/Admin ven todos).
- Response incluye pedido, mesa, items, subtotal/iva/total, y `pago` si existe (null si cuenta cerrada pero no cobrada).
- Sin UI de recibo itemizado en este spec (hallazgo #11a/b) — el endpoint queda listo para que un spec posterior lo consuma.

## Manejo de errores

- Todos los endpoints nuevos siguen el patrón ya existente del proyecto: `HTTPException` con `status_code` + `detail` en español, mismo estilo que `services/pedidos.py`/`services/ventas.py`.
- Transiciones inválidas (editar fuera de Pendiente, cerrar cuenta fuera de Listo, entregar sin pago) → 409, mensaje explícito de qué falta.
- Última línea de un pedido no se puede borrar → 409 (reutiliza el invariante de "pedido no puede quedar vacío" ya documentado en `CLAUDE.md`).

## Testing

- Backend: tests nuevos en el estilo ya existente de `api/tests/` para cada endpoint nuevo (CRUD de items, cerrar-cuenta, gate de Entregado, GET /tickets con los 3 roles). Casos clave: no se puede entregar sin pago (regresión directa del bug #4 encontrado en vivo), no se puede editar pedido fuera de Pendiente, no se puede borrar el último item, mesero solo ve sus tickets.
- Mobile: se evalúa en el plan de implementación si hace falta test unitario nuevo (ya hay precedente de `jest-expo` + `@testing-library/react-native` del rediseño de agosto) o si alcanza con verificación manual contra Docker, según lo que el plan determine viable sin dispositivo.

## Fuera de alcance

#1 (label botón), #5 (WS+onPress tarjeta cocina), #6 (validación unidad/stock inicial ingrediente), #7 (editar producto), #8 (CRUD recetas), #9 (mostrar IVA en PagoScreen), #10 (fix rango de fechas en servidor), #13 (auto-calcular monto de compra), #14 (filtro de categorías roto), #15 (ya entendido, no es bug). #11a/b (UI de recibo) queda parcialmente preparada por el endpoint `GET /tickets` de este spec pero su implementación de UI es un spec aparte.
