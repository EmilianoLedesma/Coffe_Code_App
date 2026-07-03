# Reportes avanzados, cierre de gaps CRUD y corte diario — Design

Fecha: 2026-07-03
Contexto: `.claude/CLAUDE.md` (diccionario de datos, arquitectura, reglas de negocio)

## 1. Motivación

Tres necesidades detectadas en esta sesión:

1. Los reportes financiero/inventario son útiles pero les faltan filtros y
   desgloses que sí existen en proyectos comparables (revisado
   `github.com/Arthie01/monorepo` como referencia de patrones, no como código
   a copiar).
2. Un audit paralelo (4 agentes Explore) sobre Usuarios/Productos/
   Ingredientes/Recetas encontró gaps reales de CRUD que limitan la operación
   diaria del panel admin.
3. No existe ninguna forma de generar un corte diario de caja desde el panel
   web — se pidió expresamente y requiere nueva tabla en base de datos.

## 2. Reportes — filtros y desgloses nuevos

### 2.1 Financiero (`construir_reporte_financiero`, `api/app/services/reportes.py`)

Nuevos parámetros opcionales en `GET /api/reportes/financiero{,/pdf,/xlsx}`:

- `categoria_id: int | None` — si se especifica, el ranking de margen y el
  desglose de ventas se acotan a productos de esa categoría (join
  `Producto.id_categoria`).
- `usuario_id: int | None` — si se especifica, acota ventas a pedidos
  atendidos por ese usuario (`Pedido.id_usuario`).

Desgloses nuevos, siempre incluidos en el payload (no filtrables, son vistas
agregadas del periodo ya filtrado por fecha/categoria/usuario):

- `ventas_por_categoria: list[{categoria_id, nombre, total}]`
- `ventas_por_metodo_pago: list[{metodo_pago, total}]` (join
  `Ticket → Pago → MetodoPago`)
- `ventas_por_usuario: list[{usuario_id, nombre, total}]`

**Regla dura**: los endpoints `/financiero/pdf` y `/financiero/xlsx` deben
recibir y propagar `categoria_id`/`usuario_id` igual que el endpoint JSON —
hoy el export ya reusa `construir_reporte_financiero` con los mismos
`desde`/`hasta`, así que basta con agregar los nuevos parámetros a las tres
firmas de router y pasarlos a la función de servicio. `reportes_export.py`
necesita añadir las 3 tablas nuevas a PDF y XLSX.

### 2.2 Inventario (`construir_reporte_inventario`)

- Nuevo parámetro opcional `desde`/`hasta` (el reporte de inventario hoy no
  tiene rango de fechas porque `riesgo_inventario` es un snapshot del stock
  actual, no depende de fechas).
- Nuevo desglose `ranking_consumo: list[{ingrediente_id, nombre, unidad,
  cantidad_consumida}]` — calculado a partir de `DETALLE_PEDIDOS` de pedidos
  con ticket emitido en el rango, multiplicado por `RECETAS.cantidad_requerida`
  por producto vendido, agregado por ingrediente, ordenado descendente.
  Requiere `desde`/`hasta` con default de 30 días si no se especifican (igual
  criterio que financiero).

## 3. Corte diario (nueva funcionalidad)

### 3.1 Esquema (Alembic — nueva migración)

```
CORTES_DIARIOS(
  id PK,
  fecha DATE UNIQUE NOT NULL,
  total_ventas DECIMAL,
  total_gastos DECIMAL,
  ganancia_neta DECIMAL,
  num_pedidos INT,
  num_tickets INT,
  generado_en TIMESTAMP,
  id_usuario FK -> USUARIOS   -- quién lo generó (siempre Administrador)
)
CORTE_METODOS_PAGO(
  id_corte FK -> CORTES_DIARIOS,
  id_metodo_pago FK -> METODOS_PAGO,
  monto DECIMAL
)  -- PK compuesta (id_corte, id_metodo_pago)
```

Se usa tabla hija para métodos de pago (en vez de columnas fijas) porque
`METODOS_PAGO` es catálogo abierto.

Semántica acordada con el usuario:
- Un corte por **día natural** (no por turno/cajero).
- **Solo resumen del sistema** — sin conciliación de efectivo contado
  manualmente.
- **No bloquea nada** — es un snapshot informativo; regenerar el corte de una
  fecha hace upsert (sobreescribe), no hay estado "cerrado".

### 3.2 Endpoints (`api/app/routers/cortes_diarios.py`, solo rol Administrador)

- `POST /api/cortes-diarios?fecha=YYYY-MM-DD` (default: hoy, zona horaria del
  servidor) → calcula desde TICKETS/PAGOS/GASTOS de esa fecha, hace upsert.
- `GET /api/cortes-diarios?desde=&hasta=` → lista para historial.
- `GET /api/cortes-diarios/{fecha}` → detalle (404 si no se ha generado).

### 3.3 Web-admin

Nueva pestaña "Corte diario" en el dashboard (o sección propia, a decidir en
plan de implementación): botón "Generar corte de hoy" (o elegir fecha),
tarjeta resumen + tabla de historial. Requiere entrada en `api_client.py` y
nav link en `base.html`.

## 4. Cierre de gaps CRUD (hallados por audit + verificados en vivo)

### 4.1 Categorías — sin CRUD de escritura

Hoy `api/app/routers/categorias.py` solo tiene `GET`. Agregar:
- `POST /categorias` (`CategoriaCreate`: nombre, descripcion opcional)
- `PUT /categorias/{id}` (editar nombre/descripcion/activo — soft-delete vía
  `activo=False`, sin DELETE físico dado que `PRODUCTOS.id_categoria` es FK
  NOT NULL)
- Gated a `RolNombre.ADMINISTRADOR` (a diferencia de lectura, que sigue
  abierta a los 4 roles).
- Web-admin: nueva página de gestión de categorías (blueprint + template),
  siguiendo el patrón de `productos.py`/`productos.html`.
- Nuevas requests de Postman para los 2 endpoints nuevos.

### 4.2 Usuarios — password reset inalcanzable + roles hardcodeados

- Nuevo endpoint `GET /api/roles` (`RolOut`: id, nombre) — solo requiere
  autenticación, cualquier rol puede leer el catálogo.
- `web-admin/app/blueprints/usuarios.py`: reemplazar
  `ROL_ID_POR_NOMBRE` hardcodeado por una llamada a `listar_roles()`.
- `web-admin/app/templates/usuarios.html:65-67`: quitar el `x-if="!editando"`
  del campo de contraseña — debe poder enviarse (opcional) también en modo
  edición. El blueprint ya soporta `PUT` con password porque la API lo
  acepta; solo hay que asegurarse de que un campo vacío no sobreescriba con
  string vacío (omitir la key del payload si el campo viene vacío).

### 4.3 Ingredientes — sin edición completa ni desactivación

`api/app/routers/ingredientes.py` hoy solo tiene GET(list)/POST(create)/
PUT(stock delta). Agregar:
- `GET /ingredientes/{id}` (get-one, usando el helper `_get_ingrediente_o_404`
  ya existente).
- `PUT /ingredientes/{id}` — edita `nombre`, `unidad`, `stock_minimo`,
  `costo_unitario` (no `stock_actual`, que sigue siendo solo vía `/stock`).
- `PUT /ingredientes/{id}/desactivar` (o incluir `activo` en el PUT general —
  a decidir en plan; se prefiere endpoint separado para no mezclar semántica
  de "editar datos" con "dar de baja", seguiendo el patrón de `/stock`).
- `listar()` debe filtrar `Ingrediente.activo.is_(True)` por default (igual
  que categorías/productos), con esa exclusión documentada.
- Web-admin: agregar botón "Editar" (modal, mismo patrón que productos.html)
  y "Desactivar" en `ingredientes.html` + blueprint.
- Nuevas requests de Postman.

### 4.4 Recetas — fix de navegación (no de backend)

Verificado en vivo contra el stack corriendo (`docker ps` +
`curl` autenticado): `GET /recetas/{producto_id}` responde 200, el
dropdown de ingredientes se puebla correctamente y el POST de "agregar
ingrediente" llega al endpoint real. El backend y el flujo de
`web-admin/app/blueprints/recetas.py` están completos.

El gap real es de descubribilidad: `web-admin/app/templates/productos.html`
no tiene ningún link hacia la receta de un producto — solo se llega por el
nav item "Recetas" y buscando el producto en una lista lateral. Fix: agregar
un link "Receta" en la fila de cada producto en `productos.html` que apunte a
`url_for('recetas.detalle', producto_id=producto.id)`.

## 5. Fuera de alcance (explícitamente)

- Conciliación de efectivo físico en el corte diario.
- Bloqueo/cierre inmutable de un día tras generar su corte.
- CRUD de Recetas (ya está completo, solo se toca navegación).
- Exportación a DOCX (el proyecto removió WeasyPrint deliberadamente; no se
  reintroduce una tercera librería de export sin pedirlo explícitamente).

## 6. Verificación

Dado que el usuario pidió no reiniciar el servidor corriendo hasta terminar
todos los cambios: cada pieza se verifica vía pytest (API) y pytest (Flask)
en las carpetas respectivas, más lectura estática, sin depender de recargar
los contenedores Docker en vivo. La verificación end-to-end contra el stack
corriendo (como se hizo para confirmar el flujo de recetas) se repite al
final, una sola vez, tras integrar todo.
