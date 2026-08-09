# Hallazgos restantes de la prueba en dispositivo — Diseño

**Fecha:** 2026-08-08
**Origen:** 15 hallazgos de la prueba en dispositivo real (parte 7 de la sesión 2026-08-08, ver `.superpowers/sdd/progress.md`). Los puntos #2, #3, #4, #11(base) ya se resolvieron en `docs/superpowers/specs/2026-08-08-cierre-cuenta-tickets-design.md` (mergeado a `main`). Este spec cubre los 9 hallazgos restantes accionables: #1, #5, #6, #7, #8, #9, #10, #13, #14. El #15 no requiere acción (comportamiento intencional ya confirmado).

## Alcance

Nueve piezas independientes entre sí (no comparten estado ni contrato), agrupadas en un solo spec/plan a pedido explícito del usuario. Cada una se implementa y prueba de forma aislada.

### #1 — Label del botón Mesero en HomeScreen

`mobile/screens/HomeScreen.js`: el botón que navega a `Mesas` está etiquetado "Mesero" en vez de "Mesas". Cambio de una línea: `label: 'Mesero'` → `label: 'Mesas'`, en las dos entradas donde aparece (`ROLES.Mesero` y el fallback genérico).

### #5 — Tarjeta hero de CocinaScreen: sin WS, no tocable

`mobile/screens/CocinaScreen.js`: la tarjeta grande `{pendientes} Pedidos en espera` no tiene `onPress` y solo se actualiza con `useFocusEffect` (al re-entrar a la pantalla), sin WebSocket.

- Agregar `onPress={() => navigation.navigate('ColaPedidos')}` a la `Card` hero — mismo destino que el `ListItem` "Cola de pedidos" ya existente.
- Suscribir al canal `cocina` (mismo patrón ya usado en `ColaPedidosScreen.js`: `connectToChannel('cocina', {...})` con guard `cancelado`/`cerrar` dentro de `useFocusEffect`) y refrescar `pendientes` (`getColaPendientes().then(...)`) cuando llegue el evento `nuevo_pedido`.

### #6 — Formulario de alta de ingrediente: unidad libre + sin stock inicial

`mobile/screens/InventarioScreen.js` + `mobile/api/ingredientes.js`:

- **Unidad como chips, no texto libre.** Reemplazar el `Input` de "Unidad" por un `Chip` seleccionable entre un set fijo (`g`, `ml`, `u`, `kg`, `l`) — mismo componente `Chip` ya usado en `MenuScreen`/`PagoScreen`/`GastosScreen`. Estado nuevo `unidadSeleccionada`, validación en `agregar()` exige que haya una seleccionada.
- **Campo "Stock inicial" opcional.** Nuevo `Input` numérico junto a los existentes (nombre/unidad/stock mínimo/costo unitario). `createIngrediente` en `api/ingredientes.js` deja de hardcodear `stock_actual: 0` — recibe un parámetro `stockInicial` (default `0` si el campo queda vacío) y lo manda tal cual. Backend ya acepta `stock_actual` en el POST (`ingredientes.py`, sin cambios).

### #7 — Editar producto en MenuScreen

`mobile/screens/MenuScreen.js`: no hay UI de edición, aunque `updateProducto(id, payload)` ya existe en `api/productos.js` y el backend (`PUT /productos/{id}`) ya funciona.

- Botón "Editar" (ícono `create-outline`, mismo patrón 44×44 que "Eliminar") en cada `ListItem` de producto.
- Al tocarlo, la card del formulario de arriba (hoy usado solo para "Agregar producto") entra en **modo edición**: se precarga con nombre/descripción/precio/categoría del producto tocado, el botón cambia texto a "Guardar cambios", y aparece un botón "Cancelar" para volver a modo alta. Reusa los mismos `Input`/`Chip` de categoría, evita duplicar el formulario.
- Toggle adicional para `disponible` (`Chip` "Disponible"/"No disponible" o un switch simple) — el único campo del `PUT` que el formulario de alta no cubre hoy.
- Guardar llama `updateProducto(id, {nombre, descripcion, precio_venta, id_categoria, disponible})`; al terminar, limpia el modo edición y recarga la lista.

### #8 — CRUD de recetas (Cocinero)

Backend intacto (`api/app/routers/recetas.py`, CRUD completo de `producto_ingrediente`, sin cambios). Se reescribe el plan viejo (`docs/superpowers/plans/2026-08-04-mobile-fase2b-recetas.md`, pre-rediseño de agosto) contra el estado actual:

- **Decisión de UX confirmada:** push a pantalla dedicada (no expandir/modal inline) — el punto de entrada vive en `MenuScreen` (botón "Editar receta" por producto), la edición ocurre en una pantalla nueva `RecetaScreen`.
- `mobile/api/recetas.js` — mismas 5 funciones que el plan viejo ya definía (`getRecetasPorProducto`, `crearReceta`, `actualizarReceta`, `eliminarReceta`, `eliminarRecetaCompleta`), sin cambios de contrato — el backend no se tocó.
- `mobile/screens/RecetaScreen.js` — reescrita con los componentes del rediseño de agosto (`Card`, `ListItem`, `Chip` para elegir ingrediente, `Input`, `Button`) en vez de `TouchableOpacity`/`StyleSheet` crudo del plan viejo. Mismo flujo funcional: lista de líneas de receta (ingrediente + cantidad + unidad), agregar línea nueva (chip de ingrediente + input de cantidad), editar cantidad de una línea existente, eliminar línea, botón "Eliminar receta completa" con confirmación nativa (`Alert.alert`).
- `MenuScreen.js` gana `navigation` como prop (hoy no lo recibe) y un botón "Editar receta" (ícono `list-outline` o similar) por producto, junto al de "Editar" (#7) y "Eliminar".
- Nueva ruta `Receta` en `App.js`.

### #9 — PagoScreen sin mostrar el total antes de cobrar

Desde que Task 13 (spec de cierre de cuenta) quitó el cálculo client-side del subtotal, `PagoScreen` no muestra ningún total — el Cajero cobra "a ciegas" hasta que el servidor responde.

- **Backend:** nuevo `GET /tickets/{ticket_id}` en `api/app/routers/tickets.py` — mismo gate de rol que `GET /tickets` (Mesero solo el propio, Cajero/Admin cualquiera), 404 si no existe, 403 si un Mesero pide un ticket ajeno. Devuelve `TicketOut` (subtotal/iva/total/id_mesa ya incluidos, reusa el modelo existente).
- **Mobile:** `mobile/api/tickets.js` gana `getTicket(ticketId)`. `PagoScreen` lo llama junto con `getPedido(pedidoId)` al cargar, y muestra `Subtotal`, `IVA`, `Total` (los reales, del servidor) en la card de arriba, antes de que el Cajero ingrese el monto — resuelve el hallazgo original (mostrar IVA) con datos ahora autoritativos en vez de estimados.

### #10 — Trampa de rango de fechas en reportes financieros

`api/app/routers/reportes.py::_rango_por_defecto`: cuando `hasta` llega como fecha pelada (`2026-08-08`, sin hora → parsea a `00:00:00`), el filtro excluye todas las ventas de ese día sin error visible.

- Fix server-side en `_rango_por_defecto`: si `hasta` tiene componente de hora exactamente `00:00:00.000000` (indicador de que el cliente mandó solo fecha), normalizarlo a fin de ese día (`23:59:59.999999`) antes de usarlo en el filtro. Aplica a los 3 endpoints que llaman `_rango_por_defecto` (`financiero`, `financiero_pdf`, y los demás que la usen — reusa la misma función, un solo punto de cambio).
- No se toca el caso de `hasta` con hora explícita distinta de medianoche (respeta la intención del caller).

### #13 — Monto manual en "Comprar insumo"

`mobile/screens/GastosScreen.js`: el campo `montoCompra` se llena a mano; cada ingrediente ya tiene `costo_unitario` en el backend.

- Quitar el `Input` de "Monto" de la card de compra.
- Calcular `montoCalculado = cantidadCompra * costoUnitarioDelIngredienteSeleccionado` (buscar el ingrediente en el array `ingredientes` ya cargado por `id`), mostrarlo como texto de solo lectura ("Monto: $X.XX") que se recalcula en vivo mientras el Cajero escribe la cantidad.
- `crearCompra({ingredienteId, cantidad, monto: montoCalculado})` — mismo backend, mismo contrato, el monto ahora viaja calculado en vez de tipeado.

### #14 — Chips de categoría en MenuScreen no filtran

`mobile/screens/MenuScreen.js`: `categoriaId` está atado únicamente al formulario de alta ("categoría del producto nuevo"), nunca filtra la `FlatList`.

- Separar el estado: `categoriaFormulario` (la que ya existe, para el alta) de un nuevo `categoriaFiltro` (`null` = "Todas").
- Fila de chips de filtro visible arriba de la lista (separada visualmente de los chips del formulario de alta, que quedan dentro de la card de "Agregar producto"), incluyendo un chip "Todas".
- `FlatList` usa `data={categoriaFiltro ? productos.filter(p => p.id_categoria === categoriaFiltro) : productos}` en vez del array crudo.

## Fuera de alcance

#15 (ya entendido, borrado condicional intencional, sin acción).

## Testing

- Backend (#9, #10): tests nuevos en `api/app/tests/` siguiendo el estilo ya establecido (`test_router_tickets.py` para el nuevo endpoint singular, `test_router_reportes.py`/`test_services_reportes.py` para el fix de fecha — caso límite exacto: `hasta` sin hora debe incluir ventas del mismo día).
- Mobile: sin tests de componente (convención ya establecida, sin cambios). Verificación manual contra Docker diferida al usuario, mismo patrón que el spec anterior.
