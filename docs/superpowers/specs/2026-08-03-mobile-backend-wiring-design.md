# Mobile ↔ Backend Wiring — Design

Fecha: 2026-08-03

## Contexto

`mobile/` (Expo + React Navigation) es hoy un prototipo puramente visual: cada
pantalla usa `useState` con arrays mock, `Alert.alert()` simula guardado, no
existe ningún cliente HTTP, ni almacenamiento de token, ni WebSocket. La
navegación del flujo Mesero está además rota:

- `screens/MesasScreen.js` es un duplicado accidental de
  `screens/EstadoPedidoScreen.js` (mismo contenido), no renderiza un grid de
  mesas y nunca llama `navigation.navigate('Pedido', ...)`.
- `screens/PedidoScreen.js` requiere `route.params.mesaId` pero no hay ningún
  camino de UI que se lo pase — pantalla inalcanzable.
- `screens/DetallePedidoScreen.js` (botones de cambio de estado) existe pero
  no está registrada en `App.js` — código huérfano.
- `screens/RecuperarPasswordScreen.js` no está enlazada desde `LoginScreen` y
  no hay endpoint de reset de password en la API — se deja fuera de alcance.

El backend (`api/`) ya expone el contrato completo (auth JWT, mesas, pedidos
con máquina de estados, ventas/caja/gastos/compras, productos/ingredientes/
recetas, admin/reportes/cortes/gastos-fijos, y WebSocket `/ws/{canal}` para
`mesero`/`cocina`/`caja`). Esta spec cubre la arquitectura general de wiring
más el detalle completo de la Fase 1 (Mesero). Cocina y Caja se dejan
esbozadas para specs propias posteriores, reutilizando la misma arquitectura.

## Decisiones (confirmadas con el usuario)

- **Orden:** Mesero primero, de punta a punta; Cocina y Caja después, mismo patrón.
- **Cliente HTTP:** `fetch` nativo envuelto en un helper propio — sin agregar axios.
- **Almacenamiento de token:** `expo-secure-store` (nueva dependencia, cifrado en disco), no `AsyncStorage`.
- **Descubrimiento de API:** LAN IP vía `app.config.js` (`extra.apiUrl`) — Expo Go en un teléfono físico no puede usar `localhost`.
- **WebSocket:** diferido a una pasada posterior, después de que las tres pantallas REST de Mesero estén verificadas contra la API real.
- **MesasScreen:** se reescribe como grid real de mesas (`GET /mesas`), coloreado por `estatus.nombre`.
- **EstadoPedidoScreen + DetallePedidoScreen:** se fusionan en una sola pantalla `Detalle` (registrada en `App.js`), reemplazando ambos archivos.

## Arquitectura

Archivos nuevos en `mobile/`:

- `app.config.js` — expone `extra.apiUrl` (LAN IP configurable por dev).
- `config.js` — lee `Constants.expoConfig.extra.apiUrl`, exporta `API_URL`.
- `api/client.js` — `request(path, {method, body, auth})`: adjunta
  `Authorization: Bearer <token>` desde `auth/session.js` si `auth:true`,
  parsea JSON, lanza `ApiError{status, message}` en no-2xx. Maneja 401
  limpiando sesión.
- `api/auth.js` — `login(correo, password)`.
- `api/mesas.js` — `getMesas()`.
- `api/pedidos.js` — `crearPedido(payload)`, `getPedido(id)`, `getPedidos(params)`.
- `api/productos.js` — `getProductos()` (para el menú de `PedidoScreen`).
- `auth/session.js` — `saveToken`/`getToken`/`clearToken` (expo-secure-store);
  decodifica el payload del JWT (base64, sin librería) para leer
  `rol`/`user_id`/`exp`.
- `auth/AuthContext.js` — contexto de React con `{token, rol, userId, login(), logout()}`.

Nueva dependencia: `expo-secure-store`. No se agrega axios ni socket.io en esta fase.

**Guarda de navegación por rol:** `HomeScreen` lee `rol` del contexto y solo
muestra el botón correspondiente (Mesero ve únicamente "Mesas"). No es un
guard de ruteo estricto (no hay `Navigator` anidado por rol todavía) — es
suficiente para el alcance de un prototipo académico; la autorización real ya
está garantizada por el backend (cada endpoint valida rol vía JWT
independientemente de lo que la UI muestre).

## Fase 1 — Mesero (detallado)

- **LoginScreen**: `login(correo, password)` → guarda token+rol+userId
  (SecureStore + contexto) → `navigation.replace('Home')`. Error 401 se
  muestra inline (reemplaza el `alert()` actual).
- **HomeScreen**: filtra botones por `rol`.
- **MesasScreen** (reescrita): `GET /mesas` al enfocar, grid de tarjetas de
  mesa coloreadas por `estatus.nombre` (Libre/Ocupada/Reservada), tap →
  `navigate('Pedido', {mesaId})`.
- **PedidoScreen**: `GET /productos` reemplaza el menú mock, arma
  `items[]` localmente, "Guardar" → `POST /pedidos {mesa_id, usuario_id,
  items}` → éxito → `navigate('Detalle', {pedidoId})`.
- **DetalleScreen** (nueva, fusiona EstadoPedido+DetallePedido, única
  registrada en `App.js`): `GET /pedidos/{id}` al enfocar + pull-to-refresh
  manual (WS diferido), muestra detalle y estatus. Sin botones de cambio de
  estado para Mesero (el backend solo permite que Cocina/Caja cambien
  estatus) — Mesero solo observa.
- `RecuperarPasswordScreen` queda sin enlazar (fuera de alcance, sin endpoint de backend).

## Manejo de errores

`api/client.js` centraliza: fallo de red → mensaje genérico "Sin conexión";
401 → limpia sesión y redirige a Login; 403/409/otros → muestra el `detail`
del error JSON de FastAPI inline en la pantalla (ya no `Alert.alert` para
errores de backend).

## Verificación

No hay test runner instalado en `mobile/` y agregar uno está fuera de
alcance para un wiring de UI a una API ya probada. Verificación de aceptación
manual contra el stack Docker real: login como usuario Mesero (seed), crear
un pedido real desde la app, confirmar la fila en la API/Postman/DB. Se
documenta como paso de aceptación del plan de implementación, no como suite
automatizada nueva.

## Fases futuras (esbozadas, specs propias)

- **Fase 2 — Cocina**: mismo `api/client.js`. `GET /pedidos?estado=Pendiente`,
  transiciones de estatus, `GET/PUT /ingredientes`, `POST/PUT /productos`.
- **Fase 3 — Caja**: `GET /pedidos?estado=...`, `POST /ventas`, `POST
  /gastos`, `POST /compras`, `GET /caja/resumen`.
- **Fase 4 — WebSocket**: un `ws/client.js` compartido (`ws://.../ws/{canal}?token=`)
  reutilizado por las tres pantallas para `pedido_listo`/`pedido_activado`/`nuevo_pedido`,
  agregado después de que las tres fases REST estén verificadas.
