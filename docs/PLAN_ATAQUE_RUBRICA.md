# Auditoría vs. Rúbrica de Evaluación Automatizada — Plan de Ataque para 100/100

Generado por revisión paralela (6 agentes de solo-lectura + verificación directa) contra `docs/Rubrica.md`.
Metodología: evidencia ejecutable (curl real contra `http://localhost:8010` API y `http://localhost:8020` web-admin,
con contenedores ya corriendo), no solo lectura de código. Login usados: seeds de `api/app/seed.py`
(ej. `admin@coffeecode.com` / `Admin123!`, `cocinero@coffeecode.com`, `cajero@coffeecode.com`, `mesero@coffeecode.com`).

## ACTUALIZACIÓN: 100/100 alcanzado

Los dos gaps (Usuarios y Reportes) fueron cerrados por dos agentes implementadores (`fix-usuarios`,
`fix-reportes`) y verificados de forma independiente con curl en vivo tras el cambio:

- `GET /api/usuarios/1` → 200, `GET /api/usuarios/9999` → 404 (endpoint nuevo, `api/app/routers/admin.py`).
- `DELETE /api/usuarios/{id}` → 204, soft-delete (`activo=false`) confirmado, 403 correcto para roles no-admin.
- `GET/pdf/xlsx /api/reportes/productos` → 200 x3, content-type correcto.
- `GET/pdf/xlsx /api/reportes/pedidos` → 200 x3, content-type correcto.
- Postman: carpeta nueva "08 - Admin - Usuarios" (6 requests) + 6 requests nuevas en "05 - Admin - Reportes" —
  JSON validado como correcto tras el edit concurrente de ambos agentes sobre el mismo archivo (sin corrupción,
  sin pérdida de carpetas existentes, sin renumeración).
- Suite de tests del backend: 92 passed, 0 failed (según fix-reportes; los 66 errors previos de
  `test_router_admin`/otros eran un problema preexistente de conexión a la DB de test en `localhost:5434`
  desde dentro del contenedor, no relacionado con estos cambios).

## Score final: 100/100 (100%)

| # | Criterio | Max | Score final | Estado |
|---|---|---|---|---|
| 1 | Gestión de Usuarios (CRUD) | 15 | **15** | Completo (GET/DELETE agregados) |
| 2 | Módulo de Estadísticas | 15 | **15** | Completo |
| 3 | Módulo de Reportes | 15 | **15** | Completo (Productos/Pedidos agregados) |
| 4 | Web Admin + API | 15 | **15** | Completo |
| 5 | API Módulo Cocina | 15 | **15** | Completo |
| 6 | API Módulo Caja | 15 | **15** | Completo |
| 7 | API Módulo Mesero | 10 | **10** | Completo |
| | **Total** | **100** | **100** | |

## Colección Postman: ejecución completa verificada con Newman

Se corrió la colección completa end-to-end con `newman run postman/coffee-code.postman_collection.json`
contra el contenedor real (`localhost:8010`) y se encontraron y corrigieron 3 problemas reales de la
colección (no del código de la API) que impedían un run limpio de punta a punta:

1. **Orden de "Login Admin"** — vivía en la carpeta 05 pero dos requests de la carpeta 03-Cocina
   (Crear/Actualizar Categoría) ya dependían de `{{token_admin}}`. Se movió "Login Admin" a la carpeta 01,
   como primer request de la colección.
2. **No-idempotencia en "Crear Producto" (carpeta 03-Cocina)** — el request no capturaba el ID del producto
   recién creado, así que "Actualizar Producto" y "Desactivar Producto (soft delete)" siempre apuntaban al
   producto semilla #1. En un segundo run, ese producto ya estaba desactivado, lo que hacía fallar
   "Crear Pedido" en la carpeta 02-Mesero (usa producto #1) con 409. Se agregó un test script que captura el
   ID en `producto_id_creado` y se actualizaron ambos requests para usar esa variable en vez de `producto_id`.
3. **Secuencia inválida de estados de pedido** — "Marcar Pedido como Entregado" vivía en la carpeta 02-Mesero
   y se ejecutaba antes de que Cocina transicionara el pedido a "Listo", violando la máquina de estados
   (Pendiente→En preparación→Listo→Entregado) y devolviendo 409. Se movió al final de la carpeta 03-Cocina,
   después de "Pedido -> Listo (descuenta inventario)".
4. **Email fijo en "Crear Usuario" (carpeta 08)** — colisionaba con 409 en reruns. Se cambió a
   `usuario.prueba.{{$timestamp}}@coffeecode.com` para garantizar unicidad en cada ejecución.

**Resultado de las 2 corridas consecutivas post-fix:** 53/53 requests ejecutadas, 0 fallos, 8/8 assertions
pasaron, todas las respuestas HTTP en el rango 2xx (200/201/204) — la colección ahora es completamente
idempotente y puede correrse repetidamente con el Collection Runner sin intervención manual.

## Score original (antes de la corrección) — referencia histórica

| # | Criterio | Max | Score actual | Estado |
|---|---|---|---|---|
| 1 | Gestión de Usuarios (CRUD) | 15 | **7** | Parcial |
| 2 | Módulo de Estadísticas | 15 | **15** | Completo |
| 3 | Módulo de Reportes | 15 | **7** | Parcial |
| 4 | Web Admin + API | 15 | **15** | Completo |
| 5 | API Módulo Cocina | 15 | **15** | Completo |
| 6 | API Módulo Caja | 15 | **15** | Completo |
| 7 | API Módulo Mesero | 10 | **10** | Completo |
| | **Total** | **100** | **84** | |

---

## Detalle por criterio

### 1. Gestión de Usuarios — 7/15 (gap más caro y más barato de cerrar)

**Evidencia:** `GET /api/usuarios` → 200 (4 usuarios reales), `POST`/`PUT` funcionan con validaciones reales
(`UsuarioCreate`/`UsuarioUpdate`, unicidad de correo → 409, rol inexistente → 404) en
`api/app/routers/admin.py:32-52` y `api/app/services/usuarios.py:18-66`.

**Por qué no es 15/15:**
- `GET /api/usuarios/{id}` **no existe** → confirmado 405 en vivo. La ruta `/api/usuarios/{id}` solo acepta `PUT`.
- **No existe ningún endpoint de eliminación** de usuario (ni hard-delete ni soft-delete explícito vía `activo=false`).
- **Cero requests de Postman para usuarios** (`grep -i usuarios postman/coffee-code.postman_collection.json` → 0 resultados). La regla 5 de la rúbrica es explícita: sin evidencia ejecutable documentada, el criterio no puede acreditarse como completo.

**Acción para 15/15 (prioridad #1, más barata de todas):**
1. Agregar `GET /api/usuarios/{usuario_id}` reusando `_get_usuario_o_404` ya existente en `admin.py:20-29`. Trivial, ~5 líneas.
2. Agregar `DELETE /api/usuarios/{usuario_id}` o exponer explícitamente `activo=false` vía el `PUT` existente como el mecanismo de "eliminar" (soft-delete), documentándolo como tal.
3. Agregar carpeta "Usuarios" a la colección Postman con: Crear, Listar, Obtener por ID, Actualizar, Eliminar/Desactivar — con token admin encadenado igual que las demás carpetas.

---

### 2. Módulo de Estadísticas — 15/15 ✅

**Evidencia:** `GET /api/reportes/financiero` → 200, datos reales calculados desde SQLAlchemy contra `Ticket`,
`Gasto`, `DetallePedido`, `Producto`, `Pedido` (no mock): ventas, gastos, ganancia neta, ranking de margen por
producto, ventas por categoría/usuario. `GET /api/reportes/inventario` → 200, estructura real de riesgo de stock.
Tests unitarios existentes (`test_services_reportes.py`, `test_router_reportes.py`).

**Nada que corregir.** Único hallazgo menor no bloqueante: no hay requests de Postman dedicados a
`/api/reportes/*` fuera de los de exportación — agregar 2 GETs (financiero, inventario) a Postman reforzaría
la evidencia ejecutable documentada (no baja el score, pero lo blinda).

---

### 3. Módulo de Reportes — 7/15 (segundo gap más importante)

**Evidencia:** Los 4 endpoints existentes funcionan perfecto en vivo:
```
GET /api/reportes/financiero/pdf   → 200, content-type: application/pdf
GET /api/reportes/financiero/xlsx  → 200, content-type: application/vnd.openxmlformats-...spreadsheetml.sheet
GET /api/reportes/inventario/pdf   → 200, content-type: application/pdf
GET /api/reportes/inventario/xlsx  → 200, content-type: application/vnd.openxmlformats-...spreadsheetml.sheet
```
Implementados en `api/app/routers/reportes.py:53-121` con reportlab/openpyxl. Documentados en Postman.

**Por qué no es 15/15:** la rúbrica pide explícitamente reportes de **Productos, Pedidos, Inventario** en PDF/XLSX.
Solo existen **financiero** e **inventario**. No hay un reporte dedicado de "productos" ni de "pedidos" —
el ranking de márgenes por producto vive *dentro* del reporte financiero, pero no es un reporte de productos
independiente, y no hay ningún reporte de pedidos (ej. listado de pedidos del periodo, tiempos de preparación,
estado de cada uno).

**Acción para 15/15 (prioridad #2):**
1. Agregar `GET /api/reportes/productos` + `/productos/pdf` + `/productos/xlsx` — reporte dedicado: catálogo con
   ventas totales, unidades vendidas, margen, disponibilidad, ranking. Reutiliza gran parte de la lógica ya en
   `services/reportes.py` (ranking_margen), solo hay que exponerlo como recurso propio con su exportación.
2. Agregar `GET /api/reportes/pedidos` + `/pedidos/pdf` + `/pedidos/xlsx` — reporte con listado de pedidos del
   periodo, estado, mesa, mesero, total, tiempo Pendiente→Entregado.
3. Agregar las 6 nuevas requests (2 recursos × [json, pdf, xlsx]) a Postman.

Esto también alimenta directamente la sección de "oportunidades" de estadísticas por productividad (ver abajo).

---

### 4. Web Admin + API — 15/15 ✅

**Evidencia:** Confirmado con sesión autenticada real (`correo=admin@coffeecode.com`, login vía formulario en
`/login`, no `/auth/login` directo — el campo del form es `correo`, no `correo_electronico`).
Tras login, TODAS las páginas protegidas devuelven 200 sin sesión rota: `/`, `/usuarios`, `/categorias`,
`/productos`, `/ingredientes`, `/recetas`, `/corte-diario`. Sin sesión, todas devuelven 302 → login (correcto).
`grep -rn "psycopg2|create_engine|SQLAlchemy" web-admin/app` → **0 resultados**: Flask no toca la DB directo,
todo pasa por `app/api_client.py` consumiendo la API FastAPI, cumpliendo la regla de arquitectura del CLAUDE.md.
Blueprints con CRUD completo: `auth`, `categorias`, `cortes_diarios`, `dashboard`, `ingredientes`, `productos`,
`recetas`, `reportes`, `usuarios`.

**Nada que corregir.**

---

### 5. API Módulo Cocina — 15/15 ✅

**Evidencia:** 16 requests en la carpeta "03 - Cocina" de Postman, todos con implementación verificada:
menú (productos, categorías, recetas/producto_ingrediente CRUD) y suministros (ingredientes CRUD + ajuste de
stock por delta + desactivar). Confirmado en vivo con login `cocinero@coffeecode.com`: `GET /productos`,
`/categorias`, `/ingredientes`, `/producto_ingrediente?producto_id=1` → todos 200 con datos reales.

**Gap NO bloqueante detectado (corregir de todas formas, es gratis):** en la colección Postman, "Crear
Categoria" / "Actualizar Categoria" (carpeta 03-Cocina) usan `{{token_admin}}`, pero "Login Admin" vive en la
carpeta 05 (posterior). Si se corre la colección completa top-to-bottom con Collection Runner, esas 2 requests
fallarán con 401 porque `token_admin` aún está vacío.

**Acción (barata, blinda contra "si la colección no puede ejecutarse, 0 al criterio"):**
Mover el request "Login Admin" a la carpeta 01 (Login), o duplicarlo ahí, para que el runner completo no falle.

---

### 6. API Módulo Caja — 15/15 ✅

**Evidencia:** 4 endpoints (`POST /ventas`, `POST /gastos`, `POST /compras`, `GET /caja/resumen`) con
implementación robusta: anti-pago-duplicado real (`Ticket.id_pedido` unique a nivel DB +
check explícito en `services/ventas.py:26-31` → 409), compra atómica stock+gasto en un solo `db.commit()`
(`services/gastos.py:19-35`). Confirmado en vivo: `GET /caja/resumen` → 200 con datos reales
(`total_ventas: 4392.92, total_gastos: 3500.00, ganancia_neta: 892.92`). Variables de Postman se autopueblan
vía test scripts encadenados — la colección corre de punta a punta sin config manual.

**Nada que corregir** (el hallazgo de que no hay request Postman dedicado para "Cancelado si pago falla" es
menor y no baja el score, porque el criterio pide gestión monetaria + compras, ambos cubiertos).

---

### 7. API Módulo Mesero — 10/10 ✅

**Evidencia:** 5 requests en Postman ("02 - Mesero"), todos verificados: `GET /mesas`, `POST /pedidos`,
`GET /pedidos`, `GET /pedidos/{id}`, `PUT /pedidos/{id}/estado`. Validación de pedido vacío confirmada en vivo
(`POST /pedidos` con `items: []` → 422, mensaje claro, no crashea). Liberación de mesa al entregar confirmada
por código (`services/pedidos.py:138-148`, cuenta pedidos activos antes de liberar). WebSockets **no es
esqueleto**: canales reales `nuevo_pedido`, `pedido_activado`, `pedido_listo` cableados a las transiciones de
estado ya verificadas por HTTP.

**Nada que corregir.**

---

## Plan de ataque priorizado (orden de ejecución sugerido)

1. **[Usuarios] Agregar `GET /api/usuarios/{id}` y mecanismo de eliminación/desactivación** — el fix más
   barato (reutiliza `_get_usuario_o_404` ya existente) y el que más puntos recupera de un solo golpe (+8 pts,
   de 7→15).
2. **[Usuarios] Agregar carpeta "Usuarios" completa a Postman** (crear/listar/obtener/actualizar/eliminar,
   con token admin encadenado) — sin esto, aunque el código esté perfecto, la regla 5 de la rúbrica puede
   dejar el criterio en 0 o 7 por falta de evidencia ejecutable documentada.
3. **[Reportes] Agregar reporte de Productos** (`GET /api/reportes/productos` + `/pdf` + `/xlsx`) — reutiliza
   lógica de `ranking_margen` ya calculada en `services/reportes.py`.
4. **[Reportes] Agregar reporte de Pedidos** (`GET /api/reportes/pedidos` + `/pdf` + `/xlsx`) — listado con
   estado, mesa, mesero, total, tiempos.
5. **[Reportes] Agregar las 6 nuevas requests a Postman** para las rutas de los puntos 3 y 4.
6. **[Cocina] Reordenar/duplicar "Login Admin" a la carpeta 01** en Postman para que el Collection Runner
   corra top-to-bottom sin 401s en las requests de categorías.
7. **[Estadísticas] (opcional, blindaje) Agregar 2 GETs de reportes (financiero/inventario) a Postman** —
   no sube el score pero refuerza evidencia ejecutable documentada ante un evaluador estricto.

Con los pasos 1-2 (+8 pts en Usuarios) y 3-5 (+8 pts en Reportes) el score pasa de **84/100 → 100/100**.
Los pasos 6-7 no suman puntos pero eliminan el único riesgo real de que un evaluador estricto ("si la colección
no puede ejecutarse, asignar 0") tumbe un criterio que hoy está en 15/15 por un detalle de orden en Postman.

---

## Oportunidades más allá del mínimo de la rúbrica

Recopiladas de los 7 análisis; no son requeridas para el 100/100 pero elevan el proyecto más allá de lo
mínimo pedido, como se solicitó explícitamente. Priorizadas por relación esfuerzo/valor:

**Seguridad y auditoría (alto valor, bajo esfuerzo):**
- Rate limiting / bloqueo temporal en `/auth/login` tras N intentos fallidos — un solo endpoint de login
  centraliza el acceso de los 4 roles, así que es el punto de entrada de mayor riesgo.
- Tabla `AUDITORIA_USUARIOS` (usuario_id, campo, valor_anterior, valor_nuevo, modificado_por, fecha) para
  registrar cambios sensibles (ej. cambio de rol).
- Flujo de "olvidé mi contraseña" con token de un solo uso (hoy depende 100% de que un admin esté disponible).

**Estadísticas y reportes (aprovecha lo que ya existe):**
- Serie temporal diaria/semanal (no solo periodo vs. periodo anterior) para graficar tendencia real en el
  dashboard Flask — los datos ya están, falta la agregación por fecha.
- Estadísticas de productividad por mesero/cocinero: tiempo promedio pedido→entregado, tiempo promedio en
  cocina por producto — calculable con los timestamps que ya existen en PEDIDOS/DETALLE_PEDIDOS.
- Alertas push (WebSocket o email) cuando un ingrediente cruza `stock_minimo`, en vez de depender de que el
  admin refresque `/api/reportes/inventario` manualmente — encaja con la arquitectura WS ya usada cocina→mesero.

**Operación de caja (realismo del negocio):**
- Cierre de caja con conteo físico de efectivo vs. lo calculado por sistema (diferencias faltante/sobrante),
  extendiendo el corte diario ya existente.
- Propinas (campo en PAGOS), descuentos/promociones por ítem o cupón, reembolsos/devoluciones con reversión
  de stock, split de cuenta entre comensales.

**Operación de mesero (experiencia real de cafetería):**
- Botón "llamar mesero" desde mesa vía nuevo canal WS, sin crear pedido.
- Endpoint `GET /mesas/{id}/pedidos` para historial directo por mesa.
- ETA visible calculado con promedio histórico de tiempo Pendiente→Listo.

**Permisos:**
- Permisos granulares por acción además del rol todo-o-nada actual (ej. cajero puede ver reportes de caja
  pero no financieros completos), útil si el equipo quiere escalar roles sin crear uno nuevo por cada caso.

Ninguna de estas es necesaria para el 100/100, pero cualquiera de las de "alto valor / bajo esfuerzo" (rate
limiting de login, auditoría de usuarios, alertas de stock) es razonable incluir junto con el plan de ataque
si el equipo quiere ir más allá del mínimo solicitado, como se pidió.
