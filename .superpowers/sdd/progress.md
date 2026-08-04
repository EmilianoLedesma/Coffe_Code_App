# Sesión 2026-08-04 — Implementación wiring mobile↔backend (Fases 0, 2, 3) + brainstorming Fases 2b/3b

Sesión guardada: `~/.claude/session-data/2026-08-04-*-session.tmp` (ver /save-session)

## Qué se construyó (todo mergeado a `main`)

Continuación directa de la sesión anterior (2026-08-03, ver abajo) — se dispatcharon los 4 planes de wiring ya escritos, cada uno en su propio worktree vía el Agent tool (isolation: worktree), siguiendo `superpowers:executing-plans` dentro de cada agente.

- **Fase 0 (infra + Mesero)**, dispatchada sola primero. 7 tareas commiteadas: `app.config.js`/`config.js` (API_URL configurable), `api/client.js` + `auth/session.js` (HTTP + JWT en SecureStore), `auth/AuthContext.js` + login real, `HomeScreen` filtrado por rol, `MesasScreen` real (reemplaza el duplicado roto de `EstadoPedidoScreen`), `PedidoScreen` real (`POST /pedidos`), `DetalleScreen` nueva (fusiona `EstadoPedidoScreen`+`DetallePedidoScreen`, ambos eliminados). **Bug real encontrado durante el dispatch:** el agente puso `apiUrl: 'http://<LAN_IP>:8000'` siguiendo el plan al pie de la letra, pero el contenedor Docker real mapea a **puerto 8010**, no 8000 — se corrigió con un commit extra tras el hallazgo (el agente inicialmente rechazó mi corrección enviada por `SendMessage` a mitad de tarea, pensándola una inyección de prompt; se corrigió manualmente en su worktree antes de mergear). Merge a `main` vía `finishing-a-development-branch`, verificado en vivo con Expo Go en teléfono físico contra el Docker real (login, mesas 5 Libre/3 Ocupada coincidiendo con la API, creación de pedido real #39, detalle correcto).
- **Fase 2 (Cocina) + Fase 3 (Caja)**, dispatchadas en paralelo (`superpowers:dispatching-parallel-agents`), cada una en su propio worktree, con aislamiento de archivos por diseño (`api/pedidos_cocina.js` vs `api/pedidos_caja.js`, sin tocar `api/pedidos.js` de Fase 0). Ambas completaron sus 3 tareas limpio, sin desviaciones del plan más allá de un `git merge main --ff-only` necesario al inicio (sus worktrees habían bifurcado de un punto anterior a que Fase 0 se mergeara a `main`).
  - Fase 2: `MenuScreen`/`InventarioScreen` con CRUD real, `ColaPedidosScreen`+`CocinaDetalleScreen` con cola FIFO real y cambio de estatus. **Descuento atómico de inventario verificado en vivo de nuevo**: Espresso 3880.00ml→3850.00ml (exacto a receta), los otros 15 ingredientes sin cambio byte-a-byte.
  - Fase 3: `CajaScreen`/`PagoScreen`/`GastosScreen` con cola real de pedidos "Listo", pago real vía `POST /ventas`. **Flujo completo Listo→Cobrar→Pago-exitoso verificado en vivo**: pedido #40, monto insuficiente rechazado con el mensaje exacto de la API, pago exitoso con total/cambio reales, `GET /pedidos/40` confirma `total` pasó de `null` a `81.20`.
  - Merge de ambas a `main` sin conflictos (aislamiento de archivos funcionó exactamente como se diseñó). Verificación final: bundle de Expo Web compila limpio con los 4 módulos juntos (515 módulos).
- Limpieza de worktrees: Windows bloqueó `git worktree remove` por rutas largas dentro de `node_modules` anidado — se resolvió con el truco de `robocopy /MIR` contra un directorio vacío antes de `Remove-Item`, repetido para las 3 worktrees de esta sesión.

## Hallazgos menores de esta sesión (no bugs de la API, contexto operativo)

- `mobile/.git` — un repo git anidado huérfano (probablemente de un `npx create-expo-app` que corrió `git init`), nunca trackeado por el repo principal, encontrado y eliminado al inicio de la sesión.
- `mobile/node_modules` nunca se había instalado en el checkout base (`package-lock.json` sí, `node_modules` no) — cada agente tuvo que correr `npm install` como primer paso.
- LAN IP real de la máquina (Wi-Fi): `10.16.72.248`. Puerto real del contenedor API vía `docker compose`: **8010** (no 8000, que era solo un placeholder del plan original).

## Gap encontrado por el usuario: wiring no cubre todos los endpoints listados en `CLAUDE.md`

El usuario preguntó explícitamente si algún endpoint no encajaba en las pantallas mock existentes. Verificado contra la spec original (`docs/superpowers/specs/2026-08-03-mobile-backend-wiring-design.md:104-107`) y el contrato de `CLAUDE.md`: dos endpoints se habían esbozado para Fases 2/3 pero se omitieron sin decisión explícita al escribir los planes finales, porque no encajaban en ninguna pantalla mock ya existente:

1. **`POST /compras`** (Caja) — ya implementado en el backend y en web-admin, nunca wireado a mobile.
2. **`POST/PUT/DELETE /producto_ingrediente`** (recetas, Cocina) — nunca tuvo ni siquiera una pantalla mock en el prototipo original.

**Bloqueador de backend real encontrado durante el brainstorming de Fase 3b:** `GET /ingredientes` está gateado a `COCINERO, ADMINISTRADOR` (`api/app/routers/ingredientes.py:20`) — Cajero no tiene lectura, así que no puede armar un selector de ingredientes para registrar una compra. Confirmado también por el hallazgo de la prueba de fuego de sesiones previas. Decisión del usuario: ampliar `_lectura` para incluir `CAJERO` (la escritura sigue Cocinero/Admin únicamente).

**Specs + planes escritos y commiteados esta sesión (sin implementar aún):**

- `docs/superpowers/specs/2026-08-04-mobile-fase3b-registrar-compra-design.md` + `docs/superpowers/plans/2026-08-04-mobile-fase3b-registrar-compra.md` — 3 tareas: ampliar rol en `ingredientes.py` (con test nuevo), rebuild+verificación del contenedor, `api/compras.js` + nueva sección "Comprar insumo" en `GastosScreen.js` (reutiliza `getIngredientes()` de Fase 2).
- `docs/superpowers/specs/2026-08-04-mobile-fase2b-recetas-design.md` + `docs/superpowers/plans/2026-08-04-mobile-fase2b-recetas.md` — 3 tareas: `api/recetas.js`, `RecetaScreen.js` nueva (agregar/editar/eliminar-uno/eliminar-todo, por producto), enlace desde `MenuScreen.js` + ruta en `App.js`.

**Próximo paso exacto:** dispatchar ambos planes vía `superpowers:subagent-driven-development` (un subagente fresco por tarea, con review entre tareas — NO worktree paralelo esta vez, es ejecución dentro de la sesión). Fase 3b es independiente de Fase 2b (no comparten archivos) pero **ambas dependen de que Fase 2/3 ya estén en `main`** (ya lo están, confirmado esta sesión) — Fase 2b específicamente modifica `MenuScreen.js`/`App.js` que Fase 2 creó.

---

# Sesión 2026-08-03 (parte 2) — Diseño + planificación wiring mobile↔backend (sin implementar)

Sesión guardada: `~/.claude/session-data/2026-08-03-mobilewire1-session.tmp`

`mobile/` (Expo/React Native) es hoy un prototipo 100% mock: `useState` con arrays hardcodeados, `Alert.alert()` simula guardado, cero llamadas HTTP, cero storage de token, navegación Mesero rota (`MesasScreen.js` duplica accidentalmente `EstadoPedidoScreen.js` y nunca navega a `PedidoScreen`; `DetallePedidoScreen.js` huérfano, no registrado en `App.js`). El backend (`api/`) ya está completo y probado. Se exploraron ambos lados con 2 subagentes Explore en paralelo, se brainstormeó con el usuario (4 rondas de preguntas), y se escribió:

- **Spec** (commit `410e2cb`): `docs/superpowers/specs/2026-08-03-mobile-backend-wiring-design.md` — arquitectura completa + Fase 1 (Mesero) detallada + Fases 2-4 esbozadas.
- **4 planes de implementación** (commit `5c222d6`):
  - `docs/superpowers/plans/2026-08-03-mobile-fase0-infra-mesero.md` — infra compartida (`api/client.js`, `auth/session.js`, `auth/AuthContext.js`, `config.js`/`app.config.js`) + Mesero end-to-end (login real, MesasScreen reescrito, PedidoScreen real, `DetalleScreen.js` nuevo que fusiona y reemplaza `EstadoPedidoScreen.js`+`DetallePedidoScreen.js`). **Debe correr PRIMERO y solo** — todo lo demás depende de estos 3 archivos.
  - `docs/superpowers/plans/2026-08-03-mobile-fase2-cocina.md` — Menú/Inventario/Cola de pedidos reales.
  - `docs/superpowers/plans/2026-08-03-mobile-fase3-caja.md` — Caja cobra pedidos en estatus "Listo" (no "Pendiente", confirmado contra `services/pedidos.py`), Pago real vía `POST /ventas`, Gastos (nota: no existe `GET /gastos`, limitación real de la API, no es bug).
  - `docs/superpowers/plans/2026-08-03-mobile-fase4-websocket.md` — `ws/client.js` compartido, wiring de `pedido_listo`/`nuevo_pedido`/`pedido_activado` en las 3 pantallas. **Debe correr AL FINAL**, después de que Fase 2 y Fase 3 estén ambas mergeadas.

**Regla de aislamiento clave para ejecución en paralelo:** Fase 2 y Fase 3 crean módulos API separados (`api/pedidos_cocina.js` vs `api/pedidos_caja.js`) en vez de compartir/editar `api/pedidos.js`, específicamente para poder correr en worktrees paralelos sin conflicto de merge. Decisiones de arquitectura confirmadas con el usuario: `fetch` nativo (no axios), `expo-secure-store` (no AsyncStorage), API URL vía LAN IP en `app.config.js` (Expo Go en teléfono físico no alcanza `localhost`), WS diferido a su propia fase, sin framework de tests nuevo (verificación manual contra Docker real con credenciales seed: `mesero@coffeecode.com`/`Mesero123!`, `cocinero@coffeecode.com`/`Cocinero123!`, `cajero@coffeecode.com`/`Cajero123!`).

**Estado: NO se implementó código esta sesión.** El usuario detuvo el dispatch de subagentes explícitamente para guardar sesión primero. Próximo paso exacto: dispatchar Fase 0 a un agente en su propio worktree (merge a `main` al terminar), luego Fase 2 + Fase 3 en paralelo cada una en su worktree, luego Fase 4 al final. Recordar reemplazar el placeholder de LAN IP en `app.config.js` (Fase 0 Tarea 1) por la IP real de la máquina antes de probar en Expo Go.

---

# Sesión 2026-08-03 — Verificación completa post commit 71b1792

Sesión guardada: `~/.claude/session-data/2026-08-03-coffe-verify1-session.tmp`

Rebuild de `coffee_code_api`/`coffee_code_web` a HEAD (`3da22e0`, incluye `71b1792`: productos inactivos + ajuste cancelación de pedidos), `alembic upgrade head` limpio (sin pendientes).

**Resultado: API 114/114, web-admin 44/44, 8/8 colecciones Postman en verde (202 requests, 118 assertions, 0 fails)** contra el stack Docker real reconstruido:
`coffee-code` 64/64, `fuego-rol-{admin,cajero,cocinero,mesero}` 34+16+15+11=76/76, `fuego-flujo-{pedido-completo,compra-insumos}` 19+9=28/28, `fuego-360-lectura-completa` 34/34 requests (0 assertions — smoke crawl sin `pm.test()`, solo confirma ausencia de 5xx, no valida payloads).

**Nota operativa importante:** correr pytest con `docker compose exec coffee_code_api pytest` da 96 errores falsos (`psycopg2.OperationalError: localhost:5434 connection refused`) porque los fixtures de test asumen acceso a Postgres vía host (`localhost:5434`), no vía red de contenedores. Siempre correr pytest desde el venv del host (`api/.venv/Scripts/python.exe -m pytest`, `web-admin/.venv/Scripts/python.exe -m pytest`), nunca `docker compose exec`.

Pendientes de sesiones previas (corte diario "sin info", `costo_unitario` sin recálculo automático) no re-investigados a fondo esta sesión, pero las colecciones que ejercitan esos endpoints (admin, 360) pasaron sin fallos — sin evidencia de regresión. `fuego-360-lectura-completa` sin assertions reales, pendiente decidir si se le agregan `pm.test()`.

No se modificó código esta sesión — solo verificación.

---

# Reportes API — Implementation Progress

Plan: docs/superpowers/plans/2026-07-02-reportes-api-implementation.md
Base commit before Task 1: 4b67ab3

- Task 1 (services/models: margen, ranking, riesgo de inventario): complete (commits 4b67ab3..a23e485, review clean — Approved, Minor notes below)
  - Minor: ranking_margen usa ingresos pre-IVA vs total_ventas post-IVA (dos nociones de "ingresos" en el mismo payload) — services/reportes.py:179-199
  - Minor: orden ascendente de margen_pct solo probado con 1 producto — verificar con multiples productos en review final
  - Minor: `cantidad_vendida or 1` es código muerto (calcular_top_productos nunca devuelve 0) — services/reportes.py:183
  - Minor: riesgo_inventario no filtra Producto.activo en productos_afectados — services/reportes.py:210-216
- Task 2 (reportes_export.py: reportlab PDF + openpyxl XLSX): complete (commits a23e485..a228dd7), tests pass (5/5, independently re-run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_reportes_export.py -v`) — review: **Approved with Minor findings**
  - Important: `generar_pdf_financiero`/`generar_xlsx_financiero` silently drop `margen_pct_anterior`, `variacion_ventas_pct`, `variacion_ganancia_pct` from the Task 1 payload — these period-over-period comparison fields are computed by `construir_reporte_financiero()` but never rendered in either export format, so the "trend" data disappears in the actual deliverable — services/reportes_export.py:62-107,144-176
  - Minor: no test covers the empty-list edge case for the two xlsx generators (`ranking_margen: []`, `riesgo: []`) — only `generar_pdf_inventario` has an explicit empty-riesgo test; manually verified this session that both xlsx functions and empty-ranking pdf don't crash, but there's no regression test guarding it — app/tests/test_reportes_export.py
  - Minor: `_ESTILO_TABLA`/`_tabla` will `IndexError` or render a malformed table if `ranking_margen`/`riesgo` rows have missing keys — no `.get()` defensive access, purely trusts Task 1's dict shape (acceptable given both live in the same codebase, but worth knowing before Task 3 exposes this to external report params)
  - Minor: inventario PDF combines falta+unidad into one cell (`"500 ml"`) while inventario XLSX splits them into two columns — harmless inconsistency between the two export formats, not a bug
  - No issues with the 4 signatures/return types (`dict -> io.BytesIO`, exact function names) — Task 3 can call these directly with Task 1's real output.
  - requirements.txt: `openpyxl==3.1.5` correctly added alongside `reportlab==4.2.5` even though the brief's Step 3 only mentioned reportlab explicitly — necessary and correctly pinned, no issue.
- Task 3 (router /api/reportes/*): complete (commit 8f6bdd7, tests 42/42 full suite), review clean — **Approved**, no Critical/Important/Minor findings against this task's own code.
  - Confirmed: JSON endpoints (`/financiero`, `/inventario`) preserve `margen_pct_anterior`/`variacion_ventas_pct`/`variacion_ganancia_pct` intact — Task 2's field-dropping bug is isolated to the PDF/XLSX exporters and does NOT propagate to JSON. Task 5 (dashboard) should surface trend fields from JSON even though PDF/XLSX downloads won't show them.
  - Auth: all 6 endpoints correctly gated via `require_rol(RolNombre.ADMINISTRADOR)`, no gaps.
  - Download endpoints correctly wrap `io.BytesIO` in `StreamingResponse` with correct media_type + Content-Disposition headers, verified by tests (not just 200 OK).
- Task 4 (web-admin api_client.py): complete (commit 6c93524, web-admin tests 35/35 passing excl. 1 known pre-existing WeasyPrint/GTK failure unrelated to this task), review clean — **Approved with Minor findings**.
  - Deviation from brief (correct call, verified): implementer kept `obtener_reporte_admin` instead of replacing it — still actively used by `web-admin/app/blueprints/reportes.py` and `dashboard.py`, removing it would have broken both.
  - Confirmed: `descargar_reporte` returns raw `requests.Response` (bytes/headers/status intact, no `.json()` mangling) — safe for Task 6's Flask proxy to stream.
  - Minor: `descargar_reporte` duplicates ~15 lines of `_request`'s error-handling logic instead of a shared helper — non-blocking, cosmetic.
- Task 5 (dashboard 2 pestañas): complete (commit 4603d06, web-admin tests 29/29), review clean — **Approved with Minor findings**.
  - Confirmed: Financiero tab correctly surfaces `margen_pct_anterior`/`variacion_ventas_pct`/`variacion_ganancia_pct` with defensive `None` handling; design system classes match `productos.html`/`base.html` exactly, no invented patterns; Alpine.js tab state has no staleness issue (both tabs render server-side in the same request); no XSS surface (no `|safe`, chart labels use `|tojson`).
  - Deviation (justified, self-documented, since replaced by Task 6): added a temporary bridge `exportar_financiero`/`exportar_inventario` in `reportes.py` delegating to the old `exportar_pdf`/`exportar_xlsx`, needed because the brief's own template referenced route names that didn't exist yet pre-Task-6 — verified this was a real BuildError, not over-engineering, and the bridge had no logic Task 6 needed to preserve.
  - Minor: `test_dashboard.py` doesn't assert the actual trend values (e.g. "+10.00") appear in rendered HTML, only that the section renders — matches brief's specified test exactly, not a deviation, but a future regression in the trend block wouldn't be caught.
- Task 6 (reportes.py blueprint proxy + eliminar archivos viejos): complete (commit 0b14362, web-admin tests 29/29), review clean — **Approved with Important + Minor findings**.
  - Confirmed: route names match dashboard.html's `url_for()` calls, all routes `@login_required`, invalid `formato` correctly 404s (not 500), binary passthrough uses `.content`/headers without re-encoding, deletion of `app/reportes.py` + old WeasyPrint template independently grep-verified safe (zero live references left).
  - Important (now FIXED, commit 190fa11): the global `ApiError` errorhandler in `web-admin/app/__init__.py` reused `errors/401.html` ("tu sesión expiró") for any non-401/403 status, including real API/network failures — Task 6's proxy was the first route to actually expose this to users when the API errors. Fixed by adding `errors/api_error.html` (generic message) and pointing the handler at it. Verified 29/29 tests still pass after the fix.
  - Minor: implementer's `task-6-report.md` said `requirements.txt` "still lists weasyprint" deferred to Task 7 — this was accurate at the moment the report was written, resolved moments later when Task 7 landed (`f68cf7b`) while review was in progress; not a real defect, just a timing artifact between parallel task/review dispatch.
- Task 7 (quitar WeasyPrint): complete (commit f68cf7b, web-admin tests 29/29), review clean — **Approved**, zero findings. GTK apt-get block removed cleanly from Dockerfile, no orphaned deps in requirements.txt, zero leftover WeasyPrint/GTK references anywhere in web-admin. Docker image rebuilds and starts cleanly, confirmed independently.
- Task 8 (Postman + verificación e2e): complete (commit eaab60c, API tests 42/42, web-admin tests 29/29), review clean — **Approved**, zero findings. New Postman folder `05 - Admin - Reportes` (Login Admin + 6 report requests) follows the collection's real conventions (`base_url`, new `token_admin` var — brief had assumed folder/vars that didn't exist, correctly adapted). Full Docker e2e independently re-verified by reviewer: login, both dashboard tabs, all 4 PDF/XLSX export combos via web-admin proxy, all 6 API endpoints called directly with JWT — all live-checked, not just trusted from the report.
- **PLAN COMPLETE.** All 8 tasks done and reviewed (Tasks 1,3,7,8 clean Approved; Tasks 2,4,5,6 Approved with Minor findings, one Important finding in Task 6 already fixed in follow-up commit 190fa11).
- **Final whole-branch review (commit range 4b67ab3..eaab60c, 10 commits): Ready to finish.** Zero Critical/Important. 3 Minor cross-cutting findings, 2 fixed in follow-up commit `e1c6f50` (removed orphaned `obtener_reporte_admin` in api_client.py pointing at a deleted route; deduped `_parsear_fecha` into `web-admin/app/utils.py`). Third finding (CLAUDE.md's Admin/Reportes section had a stale single-endpoint contract) fixed locally in `.claude/CLAUDE.md` (gitignored, not committed to git by design).
- Auth verified enforced at every layer end-to-end (API role check + Flask login_required + role-gated login). No orphaned WeasyPrint artifacts. Both test suites 100% green throughout (API 42/42, web-admin 29/29).
- Work done directly on `main`, no feature branch used — user confirmed `finishing-a-development-branch` (branch merge/cleanup) is not applicable here. **Plan fully closed as of commit `e1c6f50`.**

---

# Sesión 2026-07-03 (continuación) — 5 features en paralelo + corte diario + E2E

Specs: `docs/superpowers/specs/2026-07-03-reportes-crud-corte-diario-design.md`
Plans: `docs/superpowers/plans/2026-07-03-{categorias-crud,usuarios-roles-password,ingredientes-crud,reportes-filtros,corte-diario}.md`

## Qué se construyó (todo mergeado a `main`, Docker rebuild + `alembic upgrade head` ya aplicados en vivo)

- **Categorías**: CRUD completo (`POST`/`PUT /categorias`, gated a Administrador) + página web-admin.
- **Usuarios**: `GET /api/roles` nuevo; web-admin ya no harcodea IDs de rol; reset de password desde el form de edición.
- **Ingredientes**: `GET /ingredientes/{id}`, `PUT /ingredientes/{id}` (edición completa), `PUT /ingredientes/{id}/desactivar`, filtro `activo` en el listado + UI web-admin (Editar/Desactivar).
- **Reportes**: financiero ahora acepta `categoria_id`/`usuario_id` y agrega `ventas_por_categoria`/`ventas_por_usuario`/`ventas_por_metodo_pago`; inventario agrega `ranking_consumo` con rango de fechas opcional. Export PDF/XLSX propaga los mismos filtros.
- **Corte diario** (feature nueva): tablas `CORTES_DIARIOS` + `CORTE_METODOS_PAGO` (migración Alembic `2e2aaac64acf`), endpoints `POST/GET /api/cortes-diarios{,/{fecha}}` (solo Administrador), página web-admin con botón "Generar" + historial. Semántica: un corte por día natural, solo resumen (sin conciliación de efectivo), regenerable (upsert), no bloquea nada.

Todos los tests verdes tras cada merge (API 71/71 antes del fix de flush, ver abajo; web-admin 40/40 → 41/41 tras el fix de dashboard).

## Verificación E2E en vivo (mesero → cocina → caja → corte) — encontró 2 bugs reales

Flujo probado contra el stack Docker real (no solo pytest): login mesero → `POST /pedidos` (mesa 1, 2× Latte Vainilla) → cocinero `PUT /pedidos/{id}/estado` Pendiente→En preparación→Listo → caja `POST /ventas` → mesero `PUT .../estado` Entregado → `POST /api/cortes-diarios`.

**Confirmado funcionando:**
- Descuento atómico de inventario al marcar "Listo": Leche -360ml, Espresso -60ml, Jarabe de vainilla -30ml, exactos según receta × cantidad. Verificado leyendo `/ingredientes/{id}` antes/después.
- `ventas_por_metodo_pago`/`ventas_por_usuario`/`ventas_por_categoria` del reporte financiero reflejan la venta real inmediatamente (vía API).

**BUG #1 (encontrado y FIJADO esta sesión, commit pendiente de mensaje):** El dashboard de web-admin mostraba `$0.00` de ventas de HOY aunque la venta ya estaba en la API. Causa: `web-admin/app/blueprints/dashboard.py` mandaba `hasta` como fecha pelada (`date.isoformat()`, sin hora) — la API interpreta eso como medianoche (`00:00:00`), excluyendo cualquier venta posterior de ese mismo día. Esto llevaba pasando desde la sesión anterior (feature de reportes original), no es algo introducido hoy. **Fix aplicado:** `dashboard.py` ahora arma `desde`/`hasta` como `datetime.combine(fecha, time.min/time.max)` antes de llamar a la API. Test de regresión: `web-admin/tests/test_dashboard.py::test_dashboard_hasta_incluye_todo_el_dia`. Verificado en vivo tras rebuild: dashboard ya muestra `$111.36` correctamente.

**BUG #2 (encontrado y FIJADO esta sesión):** Al marcar un pedido "Entregado", la mesa debía liberarse (volver a "Libre") si no quedaban más pedidos activos en ella — pero en producción la mesa se quedaba "Ocupada" para siempre. Causa raíz: `api/app/data/db.py:7` configura `SessionLocal` con `autoflush=False`, pero `cambiar_estado_pedido` (`api/app/services/pedidos.py`) dependía implícitamente de autoflush para que la consulta de "pedidos activos" viera el cambio de estatus recién asignado (`pedido.id_estatus = nuevo_estatus.id`) antes de contar. Con autoflush apagado, la cuenta veía el estatus viejo y nunca liberaba la mesa. **El test unitario existente (`test_entregado_libera_mesa_cuando_no_hay_mas_pedidos_activos`) pasaba igual porque la sesión de tests en `conftest.py` usa `sessionmaker(bind=connection)` SIN especificar `autoflush=False`, o sea autoflush=True por default — un mismatch de configuración entre tests y producción que enmascaraba el bug.** **Fix aplicado:** `db.flush()` explícito antes de `_liberar_mesa_si_no_hay_pedidos_activos` en `cambiar_estado_pedido`. Test de regresión nuevo que fuerza `autoflush=False` en la sesión de test para replicar producción: `api/app/tests/test_services_pedidos.py::test_entregado_libera_mesa_con_autoflush_desactivado`. **Pendiente de verificar en vivo** (se encontró justo antes de que el usuario pidiera parar y guardar sesión — el fix está en código y pasa pytest, pero el contenedor `coffee_code_api` no se ha reiniciado todavía con este fix).

## BUGS/DUDAS REPORTADOS POR EL USUARIO, AÚN SIN INVESTIGAR (pendiente próxima sesión)

1. **"Los gastos no aumentan en el dashboard al ajustar/sumar cantidad a un ingrediente."** Esto casi seguro NO es un bug sino una confusión de diseño que hay que explicarle bien al usuario (y probablemente cerrar la brecha de UX):
   - `PUT /ingredientes/{id}/stock` (usado por el botón "Ajustar stock" en `web-admin/app/templates/ingredientes.html`, y también el nuevo botón "Editar" de este mismo sprint) es un ajuste de **delta puro sobre `stock_actual`**, sin monto ni concepto — NO crea ninguna fila en `GASTOS`. Ver `api/app/routers/ingredientes.py::actualizar_stock`.
   - Existe un endpoint **separado** ya implementado hace tiempo, `POST /compras` (`api/app/routers/caja.py::crear_compra` → `api/app/services/gastos.py::registrar_compra`), que SÍ hace las dos cosas juntas de forma correcta: crea un `Gasto` con `concepto=f"Compra de insumo: {nombre}"` y `monto` real, Y incrementa `ingrediente.stock_actual += cantidad`. Este es el flujo "correcto" para reflejar gasto real de inventario.
   - **El problema:** `POST /compras` NO tiene ninguna página en el web-admin (no existe `web-admin/app/blueprints/compras.py` ni template). El único control que el usuario tiene en el panel para subir stock es "Ajustar stock" (delta sin costo) — por eso nunca ve que los gastos suban, sin importar cuánto stock agregue desde la web. Esto no es un bug de cálculo, es una **página faltante**: hace falta una UI de "Registrar compra de insumo" en web-admin que llame a `POST /compras` (con `ingrediente_id`, `cantidad`, `monto`), separada del ajuste de stock sin costo.
   - Explicación de `costo_unitario` (para responder la duda del usuario sobre gramos/costo): `INGREDIENTES.costo_unitario` es el costo de referencia **por unidad de medida del ingrediente** (el campo `unidad`, ej. gramos o ml) — se usa para: (a) calcular el costo estimado de una receta (`costo_receta_producto` en `api/app/services/reportes.py`: `cantidad_requerida (en gramos/ml) × costo_unitario`), y (b) el "costo de reposición" en el reporte de riesgo de inventario (`falta × costo_unitario`). **`costo_unitario` es un valor de referencia que se edita manualmente** (ahora editable vía el nuevo `PUT /ingredientes/{id}` de esta sesión) — NO se recalcula automáticamente cuando se compra más stock a un precio distinto. O sea: si compras 1000g de café a un precio distinto al `costo_unitario` guardado, el sistema no promedia/actualiza ese costo solo; hay que editarlo a mano si cambia el precio del proveedor. Esto es una limitación de diseño a tener en cuenta, no un bug — pero vale la pena decidir si se quiere un costo promedio ponderado automático a futuro.
   - **Acción sugerida para próxima sesión:** brainstormear con el usuario si quiere (a) una página web-admin para `POST /compras` (registrar compra con gasto real), y/o (b) que `costo_unitario` se actualice automáticamente (promedio ponderado) cuando se registra una compra a un precio distinto.

2. **"El corte diario no muestra ninguna información."** No se investigó a fondo (el usuario pidió parar antes de poder revisarlo). Hipótesis a verificar primero la próxima sesión:
   - Es posible que sea simplemente que nunca se regeneró el corte de HOY después de la venta de prueba (`pedido_id=31`) — el único corte generado en esta sesión fue ANTES de esa venta (mostró `total_ventas: 0.00` correctamente para ese momento). Habría que volver a generar el corte de hoy (`POST /api/cortes-diarios`, sin `fecha` para que use hoy) y ver si el historial en `/corte-diario` lo refleja.
   - Otra hipótesis: revisar si `web-admin/app/blueprints/cortes_diarios.py::index()` tiene el mismo tipo de bug que el Bug #1 del dashboard (rango de fechas con hora truncada) al listar el historial — aunque el listado de cortes usa `CorteDiario.fecha` (columna `DATE`, no `DATETIME`), así que el bug de truncamiento horario NO debería aplicar aquí de la misma forma; pero vale la pena confirmarlo con datos reales en vez de asumir.
   - Otra hipótesis: revisar si el template `corte_diario.html` está leyendo correctamente el campo `desglose_metodos` (podría estar vacío si el corte se generó antes de tener ventas, lo cual sería correcto y no un bug).

## Estado de los contenedores Docker al momento de parar

- `coffee_code_web`: reiniciado con el fix del Bug #1 (dashboard), YA verificado en vivo mostrando `$111.36`.
- `coffee_code_api`: **el fix del Bug #2 (mesa no se libera) está en el código y pasa pytest, pero el contenedor de la API AÚN NO se reinició con ese fix** — hay que hacer `docker compose build coffee_code_api && docker compose up -d coffee_code_api` y re-probar la liberación de mesa antes de dar el Bug #2 por cerrado en producción.
- Datos de prueba en la base de datos real (no seed, se crearon en vivo durante la verificación E2E): pedido #31 (mesa 1, 2× Latte Vainilla, Entregado, con ticket/pago), categoría "Test Postres" (id 5, ya desactivada). No se hizo limpieza adicional de estos datos de prueba — quedan en la DB de desarrollo real como parte del historial de ventas.

---

# Sesión 2026-07-04 — Rebuild + Registrar compra + fix dashboard inventario + prueba de fuego multiagente + bloqueo de duplicados + reconciliación con sesión paralela

Specs: `docs/superpowers/specs/2026-07-04-{registrar-compra,bloqueo-nombres-duplicados}-design.md`
Sesión guardada: `~/.claude/session-data/2026-07-04-fuego-y-duplicados-session.tmp`

## Parte 1 — continuación de los pendientes de la sesión anterior

- **Bug #2 (mesa no se libera) reconfirmado en vivo** tras `docker compose build coffee_code_api && up -d`: flujo mesero→cocina→caja→entregado completo por curl, mesa Ocupada→Libre correctamente.
- **Feature nueva "Registrar compra"** en web-admin (brainstormeada y aprobada con el usuario): botón+modal en la página de Ingredientes que llama a `POST /compras` (ya existente en la API), separado de "Ajustar stock" (sin costo). Resuelve la duda pendiente de la sesión anterior sobre "los gastos no suben al ajustar stock". `costo_unitario` sigue siendo manual, sin recálculo automático (decisión explícita del usuario, fuera de alcance).
- **Bug real encontrado y fijado:** el dashboard de web-admin mostraba "sin datos de consumo" en la pestaña Inventario sin importar el rango de fechas — `obtener_reporte_inventario` se llamaba sin `desde`/`hasta`, y `construir_reporte_inventario` siempre devuelve `ranking_consumo: []` si faltan. Fix de una línea + su selector de fechas. Test de regresión agregado.

## Parte 2 — Prueba de fuego multiagente (los 4 roles)

Se orquestaron 3 agentes en background (agente-mesero, agente-cocinero, agente-cajero), cada uno con credenciales de un solo rol, ejecutando una batería fija de acciones legítimas + intentos deliberados de violar reglas de negocio y cruzar hacia endpoints de otros roles. La sesión principal actuó como Administrador/supervisor: rechazo del panel a un no-admin, flujo de pedido completo con 3 errores intercalados (transición inválida, monto insuficiente, pago duplicado), CRUD de usuarios/categorías, reportes JSON/PDF/XLSX, corte diario, y resolución de 2 pedidos huérfanos dejados a medio camino por los agentes.

**Resultado: 65/65 acciones (39 de agentes + 26 de supervisor) se comportaron como se esperaba, 0 bugs.** Reporte completo publicado como Artifact HTML. Hallazgos menores (no bugs): `GET /productos` no filtraba inactivos (después resuelto por la sesión paralela con `incluir_inactivos`), `GET /ingredientes` (lista completa, no solo detalle) bloqueado para Cajero.

Se construyeron 6 colecciones de Postman nuevas mirando la prueba de fuego (`fuego-rol-{mesero,cocinero,cajero,admin}`, `fuego-flujo-{pedido-completo,compra-insumos}`), generadas con un script Node (`gen_postman.js` en el scratchpad de la sesión) y verificadas con `newman` contra la API en vivo. Se encontraron y corrigieron 2 bugs reales en las colecciones mismas (no en la API): scripts de test compartiendo scope de JS entre requests en el sandbox de Newman, y un supuesto incorrecto de que Cajero puede leer `GET /ingredientes`. Se quitaron los emojis de los títulos a pedido del usuario.

## Parte 3 — Trabajo de una sesión paralela (compartido por el usuario, verificado por esta sesión)

Mientras esta sesión trabajaba, **otra sesión de Claude trabajó en paralelo sobre el mismo repositorio**. Resumen de su trabajo (tal cual lo compartió el usuario):

1. **Auditoría contra `docs/Rubrica.md`** con 6 agentes de revisión en paralelo. Score inicial 84/100 (gaps: Usuarios sin `GET /api/usuarios/{id}` ni eliminación real; Reportes sin reportes dedicados de Productos/Pedidos). Cerrados ambos gaps → 100/100. Documentado en `docs/PLAN_ATAQUE_RUBRICA.md`.
2. **3 bugs de idempotencia corregidos** en la colección Postman general (orden de login, "Crear Producto" no capturaba su ID, "Marcar Entregado" se disparaba antes de que Cocina marcara "Listo", email fijo chocando en reruns).
3. **Bug de CSS:** `corte_diario.html` y `categorias.html` usaban clases de Tailwind inexistentes en la paleta (`bg-espresso`, `text-coffee`, `border-caramel`) — texto claro sobre fondo claro, invisible. Migradas al sistema de diseño real.
4. **Eliminación real con fallback** para Recetas, Productos, Categorías, Usuarios, Ingredientes: borra de verdad si no hay historial de uso, si no, desactiva automáticamente. Todos devuelven `{eliminado, mensaje}`. Se agregó `incluir_inactivos` + badges de Estado + reactivación donde antes un elemento desactivado por el fallback quedaba invisible/inalcanzable.
5. **Dashboard:** modal de exportación granular por secciones (checkboxes) para Financiero e Inventario, PDF y XLSX. Nuevas tarjetas de detalle de gastos (por tipo/usuario) y detalle de ventas línea por línea.
6. **Feature nueva: Gastos Fijos** del local (nómina/servicios/renta/otro), CRUD + "Aplicar" (genera un Gasto real) + "Aplicar todos" en lote, exclusivo de Administrador, nueva vista `/gastos-fijos`.
7. Colección general actualizada a 64 requests / 10 assertions; `fuego-rol-admin` (la propia colección de esta sesión) extendida por ellos a 34 requests / 40 assertions cubriendo Usuarios/Categorías eliminar, Ingredientes CRUD, Recetas CRUD+eliminar-completa, Gastos Fijos, filtro de secciones y cruces de rol.
8. Migraciones: `a1f9c3d7e5b2` (soft-delete recetas) → `c7a4e8f01d33` (revertida a hard-delete) → `f3b8c1a9d4e6` (tabla gastos_fijos).

## Parte 4 — Bloqueo de nombres duplicados (tarea final de esta sesión)

El usuario reportó que las pruebas automatizadas de Postman crean ingredientes duplicados (ej. múltiples "Leche") porque no había validación de nombre único. Brainstorming con el usuario → spec aprobada → implementado:

- **Ingredientes/Productos/Categorías:** nueva verificación `_verificar_nombre_no_duplicado()` en cada router, 409 si el nombre (normalizado a minúsculas y sin espacios) ya existe en cualquier fila (activa o inactiva). Se aplica al crear y al renombrar vía `PUT` (excluyendo la propia fila). Mismo patrón que `usuarios.py` ya usaba por correo.
- **Recetas:** `POST /producto_ingrediente` deja de hacer upsert silencioso → 409 si la pareja producto+ingrediente ya existe. Nuevo `PUT /producto_ingrediente/{producto_id}/{ingrediente_id}` para editar `cantidad_requerida` sin duplicar.
- 18 tests nuevos (incluyendo `test_router_productos.py`, que no existía antes). Verificado en vivo: crear "Leche" o " LECHE " de nuevo ahora da 409.

## Parte 5 — Reconciliación final (ambas sesiones juntas)

Al terminar la Parte 4, se descubrió que el índice de git tenía mezclado (staged, sin commitear) todo el trabajo de la Parte 3, incluyendo cambios en los mismos archivos que esta sesión edita (`productos.py`, `categorias.py`, `recetas.py`, `models/productos.py`) — y los cambios de esta sesión en `ingredientes.py` ya habían quedado horneados dentro de ese staging sin forma de separarlos limpiamente. El usuario confirmó que el trabajo de la otra sesión estaba terminado y pidió comitear todo junto.

Antes de comitear se hizo una verificación completa: rebuild de contenedores, `alembic upgrade head` (hasta `f3b8c1a9d4e6`), y se encontraron **6 fallas de test preexistentes** (4 en `api/app/tests/test_reportes_export.py`, 2 en `web-admin/tests/`) causadas por fixtures desactualizados de la Parte 3 (faltaban las claves `detalle_ventas`/`detalle_gastos`/`gastos_por_tipo`/`gastos_por_usuario` en los dicts de prueba del reporte financiero, y dos mocks de `DELETE` seguían esperando `204` sin body en vez del nuevo `200 {eliminado, mensaje}`). Se corrigieron todas — la API/servicio real ya funcionaba bien, solo los fixtures de prueba estaban desactualizados.

**Estado final verificado:** API 110/110 tests, web-admin 44/44 tests, las 7 colecciones de Postman en verde contra el stack Docker real reconstruido (general 64/64 requests, fuego-rol-admin 34/34 requests/40/40 assertions — coincide exacto con lo reportado por la otra sesión), migraciones al día, 8/8 mesas Libre. Todo comiteado en un solo commit combinado: `352a0b7`.
