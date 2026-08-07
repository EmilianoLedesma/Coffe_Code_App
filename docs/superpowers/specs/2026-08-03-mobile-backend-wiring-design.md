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
- `screens/RecuperarPassword.js` no está enlazada desde `LoginScreen` y
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
  parsea JSON, lanza `ApiError{status, message}` en no-2xx. En 422 el `detail`
  de FastAPI es una lista de `{msg, loc, type}`, no un string: se unen los
  `.msg` con `'; '` (si no, el mensaje se renderiza como `[object Object]`).
  En 401 limpia la sesión y llama al handler registrado por `AuthContext`
  (`setUnauthorizedHandler`) para forzar logout + volver a Login.
- `navigationRef.js` — `createNavigationContainerRef()` de React Navigation,
  usado por `AuthContext` para el reset a Login en 401 sin que `client.js`
  conozca React Navigation.
- `api/auth.js` — `login(correo, password)`.
- `api/mesas.js` — `getMesas()`.
- `api/pedidos.js` — `crearPedido(payload)`, `getPedido(id)`,
  `cambiarEstadoPedido(id, estatus)`, `getPedidoActivoDeMesa(mesaId)`. No hay
  un `getPedidos(params)` genérico: las colas por estado viven en los módulos
  propios de cada fase (`api/pedidos_cocina.js` con `getColaPendientes()` en
  Fase 2, `api/pedidos_caja.js` con `getPedidosListos()` en Fase 3), separados
  a propósito para que las fases puedan implementarse en worktrees paralelos.
- `api/productos.js` — `getProductos()` (para el menú de `PedidoScreen`).
- `auth/session.js` — `saveToken`/`getToken`/`clearToken` (expo-secure-store);
  decodifica el payload del JWT (base64, sin librería) para leer
  `rol`/`user_id`/`exp`.
- `auth/AuthContext.js` — contexto de React con
  `{token, rol, userId, loading, login(), logout()}`. En el arranque restaura
  el token de SecureStore (descartándolo si `exp` ya venció) y registra su
  `forceLogout` en `client.js` vía `setUnauthorizedHandler`. `loading` **sí se
  consume**: `SplashScreen` espera a que sea `false` y entonces navega a
  `Home` (hay token) o `Login` (no hay) — sin `setTimeout` fijo.

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
- **MesasScreen** (reescrita): `GET /mesas` al enfocar, grid de tarjetas
  coloreadas por `estatus.nombre`. **El tap ramifica por estatus**: si la mesa
  está `Ocupada` busca su pedido activo (`GET /pedidos?estado=` para
  `Pendiente`/`En preparación`/`Listo`, filtrado client-side por `id_mesa`) y
  navega directo a `Detalle`; solo navega a `Pedido` (alta nueva) si la mesa
  está `Libre`/`Reservada`. Sin esta rama, tocar una mesa Ocupada crea un
  SEGUNDO pedido — el backend no lo bloquea (`crear_pedido` solo valida
  `Mesa.activo`).
- **PedidoScreen**: `GET /productos` reemplaza el menú mock, **filtrando
  `disponible !== false`** client-side (la API solo filtra por `activo`;
  agregar un no-disponible garantiza un 409 tardío al Guardar). Arma `items[]`
  localmente, "Guardar" → `POST /pedidos {mesa_id, usuario_id, items}` → éxito
  → `navigate('Detalle', {pedidoId, numeroMesa})`.
- **DetalleScreen** (nueva, fusiona EstadoPedido+DetallePedido, única
  registrada en `App.js`): `GET /pedidos/{id}` al enfocar + pull-to-refresh
  manual (WS diferido), muestra detalle y estatus. **Incluye el botón
  "Marcar como Entregado"** (visible solo para `Mesero`/`Administrador`, solo
  habilitado cuando `pedido.estatus.nombre === 'Listo'`), que llama
  `PUT /pedidos/{id}/estado {estatus:'Entregado'}`. El backend **sí** permite
  a Mesero cambiar estatus (`api/app/routers/pedidos.py:70-79`) y
  `Listo → Entregado` es la única transición que le queda; es además la que
  libera la mesa (`api/app/services/pedidos.py:175-177`) y la que exige el
  paso 07 de `fuego-flujo-pedido-completo` ("Mesero entrega y la mesa se
  libera"). Sin este botón ningún pedido sale nunca de `Listo`.
- **Número de mesa**: `PedidoOut` expone `id_mesa` (PK), **no**
  `numero_mesa`. Coinciden solo por accidente del seed. El flujo Mesero pasa
  `numeroMesa` como parámetro de navegación desde `MesasScreen` (que ya tiene
  el `MesaOut` completo); Cocina y Caja, que ven colas de mesas distintas sin
  parámetro disponible, hacen un `GET /mesas` y unen client-side por `id_mesa`.
- `screens/RecuperarPassword.js` queda sin enlazar (fuera de alcance, sin endpoint de backend).

## Manejo de errores

`api/client.js` centraliza: fallo de red → mensaje genérico "Sin conexión";
401 → limpia sesión, dispara `forceLogout` (reset de navegación a Login) y
lanza `ApiError`; 422 → une los `.msg` del array `detail` de FastAPI;
403/409/otros → muestra el `detail` (string) inline en la pantalla (ya no
`Alert.alert` para errores de backend).

Precedente reutilizado de `web-admin`: el 401 handler global
(`web-admin/app/__init__.py:46-52`) hace `session.clear()` + pantalla de
sesión expirada. Mobile aplica la misma semántica. El caso 422-como-array
**no** está resuelto en `web-admin/app/api_client.py:29` (mismo bug latente);
mobile lo resuelve por su cuenta y no hereda nada de ahí.

## Verificación

No hay test runner instalado en `mobile/` y agregar uno está fuera de
alcance para un wiring de UI a una API ya probada. Verificación de aceptación
manual contra el stack Docker real: login como usuario Mesero (seed), crear
un pedido real desde la app, confirmar la fila en la API/Postman/DB. Se
documenta como paso de aceptación del plan de implementación, no como suite
automatizada nueva.

## Brechas conocidas y decisiones abiertas

- **`POST /compras` desde mobile — Administrador únicamente (decisión de
  esta spec).** `POST /compras` es `Cajero|Administrador`
  (`api/app/routers/caja.py:26,53`) pero `GET /ingredientes`, necesario para
  el selector de ingrediente, es `Cocinero|Administrador`
  (`api/app/routers/ingredientes.py:20`). Un Cajero recibe 403 al listar
  ingredientes, y `fuego-rol-cajero` afirma ese 403 como comportamiento
  **correcto**. `web-admin` nunca topó con esto porque rechaza todo login que
  no sea Administrador (`web-admin/app/blueprints/auth.py:23-25`), y el propio
  `fuego-flujo-compra-insumos` incluye una request llamada "Login Admin (solo
  para leer inventario)" para sortearlo. Mobile no puede cambiar de token a
  medio flujo. **Resolución:** Fase 3 Task 4 entrega la pantalla de compras
  con el punto de entrada visible solo cuando `rol === 'Administrador'`
  (alcanzable hoy: `HomeScreen` ya renderiza Mesero/Cocina/Caja para ese rol).
  **Decisión abierta para el usuario, NO implementada:** si se quiere que un
  Cajero registre compras desde el móvil hace falta un cambio de backend
  (p. ej. abrir `GET /ingredientes` al rol Cajero, o un
  `GET /ingredientes/nombres` de solo-lectura sin costos). Eso está fuera del
  alcance de mobile y no se asume en ningún plan.
- **Cancelación de pedidos: intencionalmente fuera de alcance.** `Cancelado`
  es transición válida desde `Pendiente`, `En preparación` y `Listo`
  (`api/app/core/constants.py:36-38`) y libera la mesa igual que `Entregado`.
  Las Fases 0-4 **no** implementan ninguna UI de cancelación en móvil, por
  decisión explícita de alcance, no por omisión. Se cancela por Postman/API si
  hace falta durante las pruebas.
- **Administración pura: exclusiva de `web-admin`, no se porta a móvil.**
  `/api/usuarios`, `/api/reportes/*`, `/api/cortes-diarios`,
  `/api/gastos-fijos`, las escrituras sobre `/categorias` y
  `/producto_ingrediente` (recetas) quedan **intencionalmente** fuera de las
  cuatro fases móviles: ninguna pantalla de mobile las expone, ni siquiera para
  el rol Administrador. Es decisión de alcance, no omisión — el móvil cubre
  operación de piso (Mesero/Cocina/Caja); la administración se hace en
  `web-admin`.
- **Techo de 50 pedidos por consulta.** `GET /pedidos` usa `limit=50` por
  defecto (`api/app/routers/pedidos.py:42`) y no se envía `limit` desde
  mobile. Como los pedidos solo salen de `Listo` cuando el Mesero marca
  `Entregado`, un día ocupado puede truncar silenciosamente las colas de
  Cocina y Caja. Paginación queda fuera de alcance; se documenta como techo
  conocido, no como bug a arreglar aquí.
- **No existe `mobile/app.json`.** Fase 0 crea `app.config.js` con lo mínimo
  para Expo Go. Un futuro `expo prebuild` / build EAS necesitará reponer
  `icon`, `splash` y `assetBundlePatterns`. Fuera de alcance de este plan.
- **No hay `GET /gastos`.** Solo `POST /gastos`; `GastosScreen` acumula la
  sesión local y muestra el total autoritativo de `GET /caja/resumen`.

## Fases futuras (esbozadas, specs propias)

- **Fase 2 — Cocina**: mismo `api/client.js`. `GET /pedidos?estado=Pendiente`,
  transiciones de estatus, `GET/PUT /ingredientes`, `POST/PUT /productos`.
- **Fase 3 — Caja**: `GET /pedidos?estado=...`, `POST /ventas`, `POST
  /gastos`, `POST /compras`, `GET /caja/resumen`.
- **Fase 4 — WebSocket**: un `ws/client.js` compartido (`ws://.../ws/{canal}?token=`)
  reutilizado por las tres pantallas para `pedido_listo`/`pedido_activado`/`nuevo_pedido`,
  agregado después de que las tres fases REST estén verificadas.
