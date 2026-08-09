# Coffee Code — Revisión calificada contra requerimiento y spec

**Fecha:** 2026-08-09
**Commit evaluado:** `061fe9c` (árbol de trabajo limpio, verificado con `git status`)
**Método:** lectura directa del código actual + ejecución real de las 3 suites de pruebas. No se calificó desde documentos ni desde el log de sesiones; cada afirmación del log que se cita fue contrastada contra el código.
**Alcance:** solo lectura. No se modificó código, no se tocaron contenedores Docker.

---

## 1. Resumen ejecutivo

| Módulo (según requerimiento del evaluador) | Calificación | Justificación en una línea |
|---|---|---|
| **Módulo Cocina** (menú + inventario de suministros) | **A / 92%** | CRUD de menú, recetas e inventario completos y probados en vivo; el descuento al marcar "Listo" sí es atómico, pero permite dejar el stock en negativo sin bloqueo. |
| **Módulo Caja** (cuentas, gastos, ganancias, compras) | **A− / 88%** | Cobro, gastos y compras completos y correctos; las **ganancias no se muestran en la app móvil** (el dato se pide a la API y se descarta), solo existen en la web-admin. |
| **Módulo Cliente/Mesero** (levantamiento y surtido) | **A / 93%** | Flujo completo mesa→pedido→edición→entrega→cierre de cuenta verificado en dispositivo real, con WebSockets funcionando; falta control de propiedad: cualquier Mesero puede leer y modificar el pedido de otro. |
| **GLOBAL** | **A− / 91%** | Los 3 módulos existen, están conectados a una API real y funcionan end-to-end en dispositivo; los descuentos son por reglas de concurrencia/autorización de grano fino y por NFRs declarados pero nunca medidos. |

**Nota de contexto para el evaluador:** el requerimiento textual pide una *aplicación móvil de 3 módulos*. El proyecto entrega eso **más** una API central desacoplada y un panel web administrativo, es decir, excede el enunciado. La calificación de arriba es contra el enunciado; el apartado 6 califica el alcance ampliado de `CLAUDE.md`.

---

## 2. Resultados reales de las suites de pruebas

Ejecutadas en esta sesión, no citadas de ningún log:

| Suite | Comando | Resultado |
|---|---|---|
| API (FastAPI) | `api/.venv/Scripts/python.exe -m pytest -q` | **146 passed**, 79 warnings, 24.42s |
| Web-admin (Flask) | `web-admin/.venv/Scripts/python.exe -m pytest -q` | **50 passed**, 1.27s |
| Móvil (Jest) | `npx jest` desde `mobile/` | **22 passed**, 5 suites, 2.41s |

**Total: 218 pruebas, 0 fallas.**

Advertencia obligatoria sobre qué prueban: las 22 pruebas de Jest cubren **solo** `mobile/api/*` y `mobile/auth/*` (cliente HTTP, sesión, contexto de auth). **No existe ni una sola prueba de componente/pantalla** en el móvil — ninguna de las 17 pantallas está cubierta por prueba automatizada. Toda la confianza en la UI móvil viene de la prueba manual en dispositivo real documentada en `.superpowers/sdd/progress.md`, no de la suite.

---

## 3. Módulo Cocina — desglose por capacidad

> *"Encargado de la gestión del menú e inventario de suministros"*

| Capacidad | Tipo de evidencia | Referencias | Veredicto |
|---|---|---|---|
| Alta/baja/edición de productos del menú | prueba automatizada + código | `api/app/routers/productos.py`, `api/app/tests/test_router_productos.py`, `mobile/screens/MenuScreen.js:78-110` | **Cumple** |
| Categorías del menú | prueba automatizada | `api/app/routers/categorias.py`, `test_router_categorias.py`, `mobile/screens/MenuScreen.js:147-168` | **Cumple** |
| Baja con respaldo (borra si no hay historial, si no desactiva) | prueba automatizada | `api/app/routers/ingredientes.py:101-117` | **Cumple** — supera lo pedido |
| Bloqueo de nombres duplicados | prueba automatizada | `api/app/routers/ingredientes.py:31-40` | **Cumple** |
| Recetas producto↔ingrediente (CRUD) | prueba automatizada | `api/app/routers/recetas.py` (todo el archivo), `test_router_recetas.py`, `mobile/screens/RecetaScreen.js:67-119` | **Cumple** |
| Alta/edición de ingredientes e inventario | prueba automatizada + vivo | `api/app/routers/ingredientes.py:62-98`, `mobile/screens/InventarioScreen.js:55-99`, `mobile/screens/IngredienteDetalleScreen.js:37-68` | **Cumple** |
| Ajuste manual de stock (delta) | prueba automatizada | `api/app/routers/ingredientes.py:120-137` | **Cumple** |
| Cola FIFO de pedidos para cocina | vivo (log) + código | `api/app/routers/pedidos.py:65` (`order_by(Pedido.fecha.asc())`), `mobile/screens/ColaPedidosScreen.js` | **Cumple** |
| Transición Pendiente→En preparación→Listo | prueba automatizada + vivo | `api/app/core/constants.py:33-39`, `api/app/services/pedidos.py:226-237`, `mobile/screens/CocinaDetalleScreen.js:48` | **Cumple** |
| **Descuento atómico de receta al marcar "Listo"** | prueba automatizada + vivo | `api/app/services/pedidos.py:242-254` | **Cumple con reserva** — ver §7.1 |
| Alerta de stock bajo mínimo | prueba automatizada + vivo | `api/app/services/pedidos.py:204-205`, expuesta en `api/app/models/pedidos.py:65`, mostrada en `mobile/screens/CocinaDetalleScreen.js:56` | **Cumple** |
| Bloqueo de stock insuficiente | **ausente** | `api/app/services/pedidos.py:203` | **No cumple** — ver §7.1 |

### Verificación de la regla de atomicidad (la revisé línea por línea)

`cambiar_estado_pedido` (`api/app/services/pedidos.py:226-272`) **sí es una sola transacción**, no llamadas secuenciales que casualmente funcionan:

- `_descontar_inventario_por_receta` (línea 243) solo muta objetos ORM en memoria (`ingrediente.stock_actual = ...`, línea 203) — **no hace ningún commit propio**.
- El cambio de estatus del pedido (línea 248) y de cada ítem (línea 246) ocurre en la misma sesión.
- Existe **un único `db.commit()`** en toda la función, en la línea 254, después de todas las mutaciones. Si el descuento lanza excepción, nada se persiste.

El rollback en caso de fallo es **implícito**, no explícito: `get_db` (`api/app/data/db.py:14-19`) solo hace `db.close()` en el `finally`, sin `except: db.rollback()`. SQLAlchemy revierte la transacción abierta al cerrar la sesión, así que el comportamiento es correcto, pero `CLAUDE.md:119` describe "BEGIN/COMMIT, rollback en fallo" y el rollback no aparece escrito en ninguna parte. Funciona; no es autoexplicativo.

---

## 4. Módulo Caja — desglose por capacidad

> *"Encargado de la gestión monetaria de pedidos (cuentas, gastos, ganancias) y compras de suministros"*

| Capacidad | Tipo de evidencia | Referencias | Veredicto |
|---|---|---|---|
| Cola de cuentas por cobrar | vivo (log) + código | `api/app/routers/tickets.py:38-58` (`?pagado=false`), `mobile/screens/CajaScreen.js:24,82-105` | **Cumple** |
| Cierre de cuenta (generar ticket con subtotal/IVA/total) | prueba automatizada + vivo | `api/app/services/tickets.py:24-47`, `api/app/tests/test_services_tickets.py` | **Cumple** |
| Cobro con método de pago y cálculo de cambio | prueba automatizada + vivo | `api/app/services/ventas.py:19-71`, `mobile/screens/PagoScreen.js:56-76` | **Cumple** |
| Validación de monto insuficiente | prueba automatizada | `api/app/services/ventas.py:41-45` | **Cumple** |
| Bloqueo de pago duplicado | prueba automatizada | `api/app/services/ventas.py:29-32` **+ UNIQUE en DB** `api/app/data/pagos.py:15` | **Cumple, doble capa** |
| Recibo/ticket visual tras cobrar | vivo (esta sesión) | `mobile/screens/PagoScreen.js:97-152` | **Cumple** |
| Registro de gastos | prueba automatizada + vivo | `api/app/routers/caja.py:44-50`, `api/app/services/gastos.py:11-16`, `mobile/screens/GastosScreen.js:59-80` | **Cumple** |
| Compra de suministros (gasto + incremento de stock) | prueba automatizada + vivo | `api/app/services/gastos.py:19-35`, `mobile/screens/GastosScreen.js:82-107` | **Cumple** |
| Resumen ventas/gastos/ganancia neta (API) | prueba automatizada | `api/app/routers/caja.py:63-72`, `api/app/services/reportes.py::calcular_resumen_caja` | **Cumple** |
| **Ganancias visibles en la app móvil** | **código existe pero el dato se descarta** | `mobile/screens/GastosScreen.js:36` vs `:201` | **No cumple** — ver §7.4 |
| Ganancias/reportes en web-admin | prueba automatizada | `web-admin/app/blueprints/dashboard.py`, `web-admin/tests/test_dashboard.py` | **Cumple** (pero es web, no móvil) |
| Gastos fijos (nómina/renta/servicios) | prueba automatizada | `api/app/routers/gastos_fijos.py`, `web-admin/app/blueprints/gastos_fijos.py` | **Cumple** — supera lo pedido |
| PDF de ticket individual | prueba automatizada | `api/app/services/tickets_pdf.py`, `api/app/routers/tickets.py:70-91`, `test_router_tickets.py` | **Cumple** |

### Auditoría de seguridad del PDF de tickets (feature nueva, commit `6c1d8fc`)

Se revisó específicamente por las tres preguntas planteadas. **Las tres salen limpias:**

1. **¿El chequeo de rol/propiedad del PDF coincide con el de `GET /tickets/{id}`?**
   Sí, exactamente: ambos endpoints llaman a la **misma** función `_get_ticket_autorizado` (`api/app/routers/tickets.py:25-35`) — `obtener` en la línea 67 y `descargar_pdf` en la línea 76. No hay dos implementaciones que puedan divergir. Además comparten la misma dependencia de rol `_permiso_tickets` (línea 22), instanciada una sola vez.

2. **¿Puede un Mesero ver el PDF del ticket de otro Mesero?**
   No. `api/app/routers/tickets.py:30-33` compara `ticket.pedido.id_usuario` contra `usuario.user_id` y devuelve 403. El listado (`listar`, líneas 48-51) aplica el mismo filtro vía JOIN, así que un Mesero tampoco puede *descubrir* IDs de tickets ajenos por enumeración del listado. (Sí podría enumerar IDs a mano, pero recibiría 403 en cada uno.)

3. **¿La ruta de vista previa de Flask omite `Content-Disposition` y con eso salta autenticación?**
   No. `web-admin/app/blueprints/tickets.py:26-30` está detrás de `@login_required` y reenvía **el token del propio administrador** (`current_token()`) a la API. Omitir `Content-Disposition` solo cambia si el navegador muestra o descarga el PDF; no toca la autorización, que ocurre íntegramente del lado de la API. No hay bypass.

---

## 5. Módulo Cliente/Mesero — desglose por capacidad

> *"Encargado del levantamiento y surtido de pedidos al cliente"*

| Capacidad | Tipo de evidencia | Referencias | Veredicto |
|---|---|---|---|
| Ver mesas y su estatus | vivo (log) | `api/app/routers/mesas.py`, `mobile/screens/MesasScreen.js` | **Cumple** |
| Levantar pedido (mesa + items) | prueba automatizada + vivo | `api/app/services/pedidos.py:117-174`, `mobile/screens/PedidoScreen.js:59` | **Cumple** |
| Rechazo de pedido vacío | prueba automatizada | `api/app/models/pedidos.py:18-23` | **Cumple** |
| Agregar / editar cantidad / quitar ítem | prueba automatizada + vivo | `api/app/services/pedidos.py:53-114`, `mobile/screens/DetalleScreen.js:124-156` | **Cumple** |
| Edición bloqueada una vez en preparación | prueba automatizada | `api/app/services/pedidos.py:45-50` | **Cumple** |
| No dejar el pedido sin ítems al borrar | prueba automatizada | `api/app/services/pedidos.py:105-108` | **Cumple** |
| **N pedidos concurrentes por mesa** | vivo (log) + código | `api/app/routers/pedidos.py:63-64` (`mesa_id`), `mobile/api/pedidos.js:32-35`, `mobile/screens/PedidosMesaScreen.js` | **Cumple** — el backend lo soporta limpiamente (FK simple mesa 1:N pedidos, sin supuesto de unicidad) |
| Transición Listo→Entregado (surtido) | prueba automatizada + vivo | `api/app/services/pedidos.py:250`, `mobile/screens/DetalleScreen.js:98-108` | **Cumple** |
| Liberación de mesa al terminar | prueba automatizada + vivo | `api/app/services/pedidos.py:210-223` + `api/app/services/ventas.py:57` | **Cumple** — ver nota abajo |
| Cierre de cuenta desde el móvil | vivo (log) | `api/app/routers/pedidos.py:137-144`, `mobile/screens/DetalleScreen.js:110-122` | **Cumple** |
| **Propiedad del pedido (un Mesero no ve/edita los de otro)** | **ausente** | `api/app/routers/pedidos.py:47-134` | **No cumple** — ver §7.3 |

### Regla de liberación de mesa — verificada, es correcta y no trivial

La regla vive en **un solo lugar**: la property `Pedido.ocupa_mesa`, consumida tanto por `_liberar_mesa_si_no_hay_pedidos_activos` (`api/app/services/pedidos.py:218`) como por el filtro del móvil (`mobile/api/pedidos.js:34`). Esto es exactamente lo que especifica `docs/superpowers/specs/2026-08-09-reordenar-entrega-cobro-design.md` §4-6, y coincide con el código actual.

Dos detalles que confirman que fue depurado a conciencia y no solo escrito:
- `db.flush()` explícito en la línea 251 antes de contar pedidos activos — necesario porque `SessionLocal` usa `autoflush=False` (`api/app/data/db.py:7`); sin esto la consulta vería el estatus viejo.
- `.populate_existing()` en la línea 213 — evita que el *identity map* de SQLAlchemy devuelva `Pedido`/`Ticket`/`Pago` cacheados con estado obsoleto.

Ambos son bugs reales que ya fueron encontrados y corregidos; están en el código actual.

### Cableado de WebSockets — verificado nombre por nombre, sin desajustes

Se cruzaron todas las emisiones del backend contra todos los listeners del móvil. **Coinciden 5 de 5, en evento y en canal:**

| Evento | Emite (backend) | Canal | Escucha (móvil) |
|---|---|---|---|
| `nuevo_pedido` | `services/pedidos.py:170-173` | `cocina` | `CocinaScreen.js:30-32`, `ColaPedidosScreen.js:45-47` |
| `pedido_activado` | `services/pedidos.py:258-260` | `mesero` + `caja` | `PedidosMesaScreen.js:53`, `CajaScreen.js:47` |
| `pedido_listo` | `services/pedidos.py:261-270` | `mesero` | `DetalleScreen.js:78`, `PedidosMesaScreen.js:54` |
| `cuenta_cerrada` | `services/tickets.py:43-46` | `caja` | `CajaScreen.js:47` |
| `pedido_pagado` | `services/ventas.py:62-70` | `mesero` | `PedidosMesaScreen.js:47,55` |

Los tres eventos que exige `CLAUDE.md:113` (`nuevo_pedido`, `pedido_listo`, `pedido_activado`) están presentes; los otros dos son adicionales. El canal se valida contra el rol del JWT del lado del servidor (`api/app/routers/websockets.py:9-32`), no solo del lado del cliente. **No encontré ningún desajuste silencioso de nombres.**

---

## 6. Checklist de NFRs de `CLAUDE.md`

| NFR (`CLAUDE.md:115-122`) | ¿Realmente exigido/medido? | Evidencia |
|---|---|---|
| Login < 2s | **Solo afirmado, nunca medido** | No existe ninguna prueba de tiempo en el repo. Se buscó `ws_flow_test.py` y cualquier archivo `*perf*`: **no existen**. |
| Mesas < 1.5s | **Solo afirmado, nunca medido** | Igual que arriba. |
| Notificaciones WS < 2s | **Solo afirmado, nunca medido** | El mecanismo es push directo (`asyncio.run_coroutine_threadsafe`, `websockets/manager.py:41`), sin polling ni colas — es plausible que cumpla, pero no hay medición. |
| Reportes < 3s (rango ≤ 6 meses) | **No exigido ni medido** | No hay validación del rango de 6 meses en ninguna parte: `api/app/routers/reportes.py:45` solo aplica un default de 30 días; nada rechaza ni acota un rango mayor. |
| Pedido vacío prohibido (mín. 1 ítem) | **Genuinamente exigido** | `api/app/models/pedidos.py:18-23` al crear; `api/app/services/pedidos.py:105-108` al borrar el último ítem. |
| Pagos duplicados prohibidos | **Genuinamente exigido, doble capa** | Chequeo en `services/ventas.py:29-32` + restricción `unique=True` en `api/app/data/pagos.py:15`. Aun con una carrera, la DB lo rechaza. |
| Descuento de stock atómico | **Genuinamente exigido** (con reserva) | Un solo `db.commit()`, `services/pedidos.py:254`. Ver §3 y §7.1-7.2. |
| bcrypt + salt | **Genuinamente exigido** | `api/app/security/auth.py:10` (`CryptContext(schemes=["bcrypt"])`); bcrypt genera salt por hash automáticamente. |
| JWT en `Authorization: Bearer` | **Genuinamente exigido** | `HTTPBearer` en `api/app/security/auth.py:11`; payload con `user_id`/`rol`/`exp` 24h en las líneas 22-25. |
| Autorización por rol en backend, no solo en frontend | **Genuinamente exigido** | `require_rol` (`api/app/security/auth.py:59-68`) aplicado como dependencia en **todos** los routers revisados. El móvil solo oculta botones (`mobile/screens/HomeScreen.js:8-17`), pero la API rechaza igual con 403. |
| Migraciones Alembic versionadas | **Cumple** | 5 migraciones en `api/alembic/versions/`, sin `create_all` en el arranque (`api/app/main.py`). |
| Secretos en `.env`, nunca hardcodeados | **Cumple** | `api/app/core/config.py` exige `database_url` y `jwt_secret` por entorno, sin default. |

**Balance de NFRs: 8 de 12 genuinamente exigidos en código; los 4 de latencia están declarados en el documento y nunca fueron medidos.** Para un entregable académico esto es normal, pero si el evaluador pregunta "¿cómo saben que el login tarda menos de 2s?", hoy no hay respuesta con evidencia.

### Alcance del entregable (`CLAUDE.md:124-134`)

| Punto | Estado |
|---|---|
| 1. API funcional completa | **Cumple** — 15 routers, 146 pruebas verdes |
| 2. Frontend móvil con los 3 módulos y navegación por rol | **Cumple** — 17 pantallas, navegación derivada del rol en `HomeScreen.js:8-17` |
| 3. Web Flask (usuarios/roles + estadísticas + PDF/XLSX) | **Cumple** — 14 blueprints, 50 pruebas verdes, sin acceso directo a la DB (todo vía `api_client.py`) |
| 4. Colección de Postman de Cocina/Caja/Mesero | **Cumple, con un hueco** — ver §7.7 |

La colección `postman/coffee-code.postman_collection.json` tiene 9 carpetas y ~60 requests, cubriendo Mesero (8), Cocina (19) y Caja (5) — que es lo exigido — más Admin, que `CLAUDE.md` explícitamente exime. Las rutas revisadas coinciden con los endpoints actuales, no con versiones viejas.

---

## 7. Hallazgos concretos (todos verificados leyendo el código, ninguno es una sospecha)

### 7.1 — El descuento de inventario permite stock negativo, contradiciendo al ajuste manual
**`api/app/services/pedidos.py:200-207`** · Severidad: **media**

```python
ingrediente.stock_actual = ingrediente.stock_actual - cantidad_necesaria
if ingrediente.stock_actual < ingrediente.stock_minimo:
    alertas_stock_bajo.append(ingrediente.nombre)
```

No hay ninguna comprobación de que alcance el stock. Marcar "Listo" un pedido sin insumos deja `stock_actual` en negativo silenciosamente; solo se emite una alerta informativa.

Lo que lo convierte en hallazgo y no en decisión de diseño es la **inconsistencia interna**: el ajuste manual de stock sí bloquea el negativo, con 409, en `api/app/routers/ingredientes.py:129-133` ("El ajuste dejaría el stock en negativo"). O sea, el sistema prohíbe por la puerta del frente exactamente lo que permite por la puerta de atrás. Un negativo en `stock_actual` además envenena el reporte de riesgo de inventario, que calcula costo de reposición como `falta × costo_unitario`.

### 7.2 — El descuento es atómico pero no está aislado: dos "Listo" concurrentes pueden perder una actualización
**`api/app/services/pedidos.py:200-203`** · Severidad: **baja** (académicamente), **media** (en producción)

Los ingredientes se leen con un `SELECT` normal, sin `with_for_update()`. Bajo el nivel de aislamiento por defecto de PostgreSQL (READ COMMITTED), dos cocineros marcando "Listo" a la vez pueden leer el mismo `stock_actual`, restar cada uno lo suyo y que la última escritura pise a la primera — un *lost update* clásico. Cada transacción es atómica por separado; lo que falta es serialización entre ellas.

`CLAUDE.md:119` solo exige atomicidad, así que esto **no incumple la spec literalmente** — pero es la diferencia entre "atómico" y "correcto bajo concurrencia", y con una sola cocina es exactamente el escenario que puede ocurrir. Arreglo mínimo: `.with_for_update()` en la consulta de la línea 200.

### 7.3 — Cualquier Mesero puede leer y modificar los pedidos de cualquier otro Mesero
**`api/app/routers/pedidos.py:47-134`** · Severidad: **media**

Ninguno de `listar`, `obtener`, `cambiar_estado`, `agregar_item`, `actualizar_item`, `eliminar_item` ni `cerrar_cuenta_endpoint` filtra por `Pedido.id_usuario`. Un Mesero autenticado puede pedir `GET /pedidos/{cualquier_id}`, borrarle ítems o cerrarle la cuenta a un pedido levantado por otro mesero.

Esto destaca precisamente porque **el mismo proyecto sí implementa bien ese control en otro lado**: `api/app/routers/tickets.py:30-33` compara `ticket.pedido.id_usuario != usuario.user_id` y responde 403. El patrón existe y está probado; simplemente no se aplicó a pedidos. Puede ser intencional (en una cafetería chica los meseros se cubren entre sí), pero no está documentado como decisión en ningún spec, así que lo reporto como brecha.

### 7.4 — La app móvil de Caja no muestra ganancias, aunque el dato llega del servidor
**`mobile/screens/GastosScreen.js:32-42` y `:199-203`** · Severidad: **media** (impacta directo al requerimiento del evaluador)

`cargarResumen` llama a `getResumenCaja(desde)`, que devuelve `{total_ventas, total_gastos, ganancia_neta}` (`api/app/models/ventas.py:66-71`). Pero la línea 36 guarda **solo un campo**:

```python
setTotalPeriodo(resumen.total_gastos);
```

`total_ventas` y `ganancia_neta` se reciben y se tiran. La única cifra que ve el Cajero en el celular es "Total gastos de hoy" (línea 201).

El requerimiento textual del evaluador dice que el Módulo Caja gestiona *"cuentas, gastos, **ganancias**"*. Las ganancias existen en la API y se muestran en el dashboard web, pero **no en la aplicación móvil**, que es lo que el enunciado pide. Es el hallazgo con más peso para la calificación: el arreglo son dos líneas y cierra un hueco literal del enunciado.

### 7.5 — Texto obsoleto en la pantalla de Caja tras el reordenamiento entrega/cobro
**`mobile/screens/CajaScreen.js:89`** · Severidad: **baja**

> "Sin cuentas por cobrar. Aparecerán aquí cuando el Mesero cierre la cuenta de un pedido **Listo**."

Desde el cambio del 2026-08-09, cerrar cuenta exige estatus **Entregado**, no Listo (`api/app/services/tickets.py:25-29`, y el móvil lo refleja en `DetalleScreen.js:180`). El mensaje quedó desactualizado y le enseña el flujo equivocado al Cajero.

### 7.6 — El rollback de la transacción es implícito, no explícito
**`api/app/data/db.py:14-19`** · Severidad: **muy baja** (funciona correctamente)

```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Sin `except: db.rollback()`. El comportamiento es correcto — `Session.close()` revierte la transacción pendiente — pero `CLAUDE.md:119` habla de "BEGIN/COMMIT, rollback en fallo" y no hay ninguna línea de rollback que un evaluador pueda señalar. Vale la pena agregarla aunque sea redundante, porque es literalmente lo que la rúbrica va a buscar.

### 7.7 — El endpoint nuevo de PDF de ticket no tiene request en Postman
**`postman/coffee-code.postman_collection.json`** · Severidad: **baja**

`GET /tickets/{id}/pdf` (agregado en el commit `6c1d8fc` de hoy) no aparece en la colección. Se enumeraron las 9 carpetas y sus ~60 requests: la carpeta "04 - Caja" incluye `GET /tickets?pagado=false` pero ningún request de PDF. Incumple la convención de `CLAUDE.md:145` ("cada endpoint nuevo debe acompañarse de su request de Postman").

### 7.8 — `CLAUDE.md` describe un contrato de `/ventas` que ya no es el que el código implementa
**`.claude/CLAUDE.md:89` vs `api/app/models/ventas.py:7-10`** · Severidad: **baja** (deriva documental, no bug)

`CLAUDE.md` especifica `POST /ventas → {pedido_id, metodo_pago, monto}` y dice que "pasa pedido a *Pendiente* (cola cocina)". El código real recibe **`ticket_id`** (no `pedido_id`) y no cambia el estatus del pedido en absoluto — el cobro es el último paso, no el primero.

Esto **no es un defecto del código**: el flujo fue rediseñado deliberadamente, con spec aprobada (`docs/superpowers/specs/2026-08-09-reordenar-entrega-cobro-design.md`) tras una prueba en dispositivo real. Lo que quedó desactualizado es `CLAUDE.md`. Importa porque, si el evaluador califica el código contra el contrato de endpoints de `CLAUDE.md` al pie de la letra, va a marcar como incumplimiento algo que en realidad es una mejora. **Recomendación: actualizar `CLAUDE.md:89` antes de entregar.**

### 7.9 — La ventana de "cuenta ya cerrada" puede devolver 500 en vez de 409 bajo carrera
**`api/app/services/tickets.py:31-35`** · Severidad: **muy baja**

Hay un lapso entre el `SELECT` que verifica si ya existe ticket (línea 31) y el `INSERT` (línea 39). Dos peticiones simultáneas de "cerrar cuenta" pueden pasar ambas la verificación. **Los datos están a salvo** — `api/app/data/tickets.py:18` declara `unique=True` en `id_pedido`, así que la segunda inserción falla en la base de datos. El único efecto es que el usuario recibiría un 500 (IntegrityError) en vez del 409 amable. La integridad nunca se rompe.

### 7.10 — Cero cobertura automatizada de pantallas móviles
**`mobile/`** · Severidad: **media** como riesgo, no como defecto

Las 5 suites de Jest cubren `api/client`, `api/pedidos`, `api/tickets`, `auth/session`, `auth/AuthContext`. Las 17 pantallas de `mobile/screens/` no tienen ni una prueba. `docs/superpowers/specs/2026-08-09-reordenar-entrega-cobro-design.md:57` lo declara convención explícita ("Mobile: sin tests de componente"), así que es una decisión consciente y no un descuido — pero significa que **cualquier regresión de UI solo se detecta probando a mano en el celular**. Los bugs de UI encontrados esta sesión (el remount del teclado en Gastos, el scroll de Menú/Receta) son exactamente la clase de fallo que esto deja pasar.

### Nota sobre el arreglo del teclado en `GastosScreen` (solicitado explícitamente)

**El arreglo es correcto.** `mobile/screens/GastosScreen.js:222` pasa `ListHeaderComponent={renderHeader()}` — **invocando** la función y entregando un elemento ya construido. Esa es la corrección adecuada: si se pasara `renderHeader` (la referencia a la función), React Native lo trataría como un *tipo de componente*, y como la identidad de la función cambia en cada render, React desmontaría y remontaría todo el encabezado en cada pulsación de tecla, cerrando el teclado. Al pasar un elemento, la reconciliación ocurre por posición dentro de un `Fragment` estable y los `Input` conservan su identidad. Complementado correctamente con `keyboardShouldPersistTaps="handled"` (línea 221) y `KeyboardAvoidingView` con `behavior` por plataforma (líneas 213-216).

---

## 8. Contraste con `.superpowers/sdd/progress.md`

Se verificaron contra el código las afirmaciones "confirmado funcionando" del log. **El log resultó confiable: no encontré ni un solo caso de sobreafirmación.** Al contrario, encontré dos casos donde el log se quedó *corto*:

| Afirmación del log | Verificación contra el código actual | Veredicto |
|---|---|---|
| "Pendiente: al pagar no se emite ningún WebSocket al Mesero" (cierre de sesión 2026-08-09) | **Ya está implementado**: `api/app/services/ventas.py:62-70` emite `pedido_pagado` con `mesa_liberada`, y `mobile/screens/PedidosMesaScreen.js:47-48` lo escucha y navega de vuelta a Mesas. Commit `fb20ea8`. | Log **desactualizado** (subestima); el código va por delante |
| "Tests backend: 143/143 verde" | Hoy son **146/146**. Se agregaron pruebas después de escribir esa línea. | Log **desactualizado** (subestima) |
| "`_liberar_mesa_si_no_hay_pedidos_activos` reescrita contando `ocupa_mesa`, con `.populate_existing()`" | Confirmado literalmente en `services/pedidos.py:210-223` | **Exacto** |
| "Se agregó la liberación de mesa también en `registrar_venta`" | Confirmado en `services/ventas.py:57` | **Exacto** |
| "`getPedidosActivosDeMesa` filtra por `p.ocupa_mesa`" | Confirmado en `mobile/api/pedidos.js:34` | **Exacto** |
| "`db.flush()` explícito antes de contar pedidos activos (bug de `autoflush=False`)" | Confirmado en `services/pedidos.py:251`, y `autoflush=False` confirmado en `data/db.py:7` | **Exacto** |
| "`DetalleScreen.puedeCerrarCuenta` pasa de `esListo` a `esEntregado`" | Confirmado en `mobile/screens/DetalleScreen.js:180` | **Exacto** |
| "Descuento atómico verificado en vivo, exacto según receta × cantidad" | La lógica de `services/pedidos.py:190-195` efectivamente multiplica `cantidad_requerida × detalle.cantidad` y agrega por ingrediente | **Exacto** |

Una observación de proceso: el log distingue con honestidad entre lo probado en dispositivo real, lo probado solo con pytest y lo pendiente — incluso deja escritos los bugs que encontró y **no** alcanzó a arreglar. Esa disciplina es lo que hizo posible esta revisión; es evidencia de calidad del proyecto por derecho propio.

Aclaración sobre `git status`: al iniciar la revisión, 7 archivos de `mobile/screens/` aparecían modificados sin commitear. Al re-verificar, el árbol estaba limpio — esos cambios se commitearon durante la sesión (`b704669`, `6c1d8fc`, `061fe9c`). **Todo lo evaluado en este documento corresponde a código commiteado.**

---

## 9. Qué arreglar antes de entregar, en orden de retorno

1. **Mostrar ventas y ganancia neta en `GastosScreen`** (`mobile/screens/GastosScreen.js:36`) — dos líneas, y cierra la única palabra del requerimiento textual del evaluador que hoy no está en la app móvil. Máximo retorno por esfuerzo de toda la lista.
2. **Actualizar `CLAUDE.md:89`** al contrato real de `/ventas` (`ticket_id`, cobro al final) — evita que el evaluador marque como defecto un rediseño que fue deliberado y está documentado con spec.
3. **Corregir el texto obsoleto** de `CajaScreen.js:89` ("Listo" → "Entregado") — una palabra.
4. **Bloquear el stock negativo** en `services/pedidos.py:203`, o documentar explícitamente por qué se permite; hoy contradice a `ingredientes.py:129`.
5. **Agregar el request de `GET /tickets/{id}/pdf`** a la colección de Postman.
6. *(Opcional, si sobra tiempo)* Un `.with_for_update()` en `services/pedidos.py:200` y un `except: db.rollback()` en `data/db.py` — ambos de una línea, y ambos son exactamente lo que una rúbrica de "transacciones" busca literalmente.

---

## 10. Conclusión

Este es un proyecto en buen estado, con evidencia real detrás. Los tres módulos que exige el enunciado existen, están conectados a una API central genuinamente desacoplada y se probaron end-to-end en un dispositivo físico, no solo con pruebas unitarias. 218 pruebas automatizadas en verde, migraciones versionadas, secretos fuera del código, autorización aplicada en el servidor y no solo escondiendo botones, y WebSockets cuyos nombres de evento coinciden exactamente entre backend y móvil en los 5 casos.

Lo que separa un 91% de un 97% no es arquitectura, es acabado: una cifra que se pide al servidor y se descarta antes de mostrarla, un control de propiedad que el proyecto ya sabe implementar y que no se aplicó a `/pedidos`, un límite de stock que se exige en una ruta y se ignora en otra, y cuatro NFRs de latencia que están escritos pero nunca se midieron. Los seis arreglos del apartado 9 suman menos de una hora de trabajo y ninguno requiere cambios de diseño.
