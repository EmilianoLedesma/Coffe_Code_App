# Reportes del Dashboard — Mover lógica a la API (Diseño)

**Fecha:** 2026-07-02
**Estado:** Aprobado, pendiente de plan de implementación

## Contexto

El Web Admin (Flask) ya tiene un dashboard funcional con 3 bloques: salud
financiera, rendimiento de producto (margen) y riesgo de inventario, más
exportación a PDF (WeasyPrint) y XLSX (openpyxl). Toda esa agregación y
generación de archivos vive hoy en `web-admin/`, lo cual viola la regla de
arquitectura de `.claude/CLAUDE.md`: *"Toda la lógica de negocio vive en
FastAPI. Flask y React Native son clientes."*

Se revisó un proyecto de referencia (monorepo Macuin: FastAPI + Flask +
Laravel para una tienda de autopartes) que resuelve reportes así: FastAPI
expone endpoints `GET /v1/reportes/datos/{tipo}` (JSON, para gráficas) y
`GET /v1/reportes/{tipo}/{formato}` (descarga binaria, generada con
reportlab/openpyxl/python-docx dentro de la API). Flask solo hace fetch del
JSON para pintar el dashboard, y hace *proxy* de la descarga con
`send_file(BytesIO(resp.content))` — cero lógica de negocio ni generación de
archivos en Flask.

Este documento adapta ese patrón a Coffee Code, sin copiar el dominio de
Macuin (no tenemos "pedidos" ni "usuarios" como reportes — esos ya son CRUD
puros en nuestro alcance).

## Objetivo

1. Mover todo el cálculo de reportes (margen, ranking, riesgo de inventario)
   de `web-admin/app/reportes.py` a `api/app/services/reportes.py`.
2. Exponer en FastAPI endpoints JSON + endpoints de descarga (PDF/XLSX) por
   categoría de reporte, protegidos con el JWT + rol Administrador ya
   existente (sin introducir HTTPBasic ni otro esquema de auth).
3. Cambiar la generación de PDF de WeasyPrint a **reportlab** (tablas
   nativas, sin dependencia de GTK — elimina el problema de
   `libgobject-2.0-0` en Windows que ya nos costó tiempo en la sesión
   anterior).
4. Reorganizar el dashboard de Flask en 2 pestañas: **Financiero** (ventas,
   gastos, ganancia neta, margen %, variación vs. periodo anterior,
   rendimiento de producto) e **Inventario** (riesgo de stock), cada una con
   su propio filtro de fechas y sus propios botones de descarga PDF/XLSX.
5. Mantener solo 2 formatos de exportación (PDF, XLSX) — no se agrega DOCX.

## Fuera de alcance

- No se tocan los reportes de "usuarios" o "pedidos" al estilo Macuin — no
  aplican al dominio de Coffee Code tal como está definido en
  `.claude/CLAUDE.md`.
- No se agrega python-docx ni exportación DOCX.
- No se cambia el esquema de autenticación (sigue siendo JWT Bearer +
  `require_rol(Administrador)`, no HTTPBasic).
- No se rediseña visualmente el sistema de diseño ya aplicado (paleta
  Starbucks-inspirada de `.claude/DESING.md`); las 2 pestañas nuevas
  reutilizan los mismos componentes (`.card`, `.btn`, `.data-table`, badges).

## Arquitectura

### API (FastAPI) — nuevo router `api/app/routers/reportes.py`

```
GET /api/reportes/financiero?desde=&hasta=   → JSON (financiero + ranking margen)
GET /api/reportes/inventario                 → JSON (riesgo de inventario)
GET /api/reportes/financiero/pdf?desde=&hasta=
GET /api/reportes/financiero/xlsx?desde=&hasta=
GET /api/reportes/inventario/pdf
GET /api/reportes/inventario/xlsx
```

Todos protegidos con `Depends(require_rol(RolNombre.ADMINISTRADOR))`, igual
que el resto de `/api/*`.

**`api/app/services/reportes.py`** gana las funciones que hoy viven en
`web-admin/app/reportes.py` (movidas tal cual, adaptadas a operar sobre
modelos SQLAlchemy en vez de dicts de respuesta HTTP):
- `calcular_margen_pct`, `variacion_pct`, `periodo_anterior` (ya existen
  parcialmente o se adaptan)
- `costo_receta_producto(db, producto_id)` — reemplaza el loop N+1 de Flask
  con una sola consulta a `RECETAS` join `INGREDIENTES` por producto
- `calcular_ranking_margen(db, desde, hasta)` — combina
  `calcular_top_productos` existente con el costo de receta por producto
- `calcular_riesgo_inventario(db)` — reemplaza
  `mapa_ingrediente_a_productos` + `riesgo_inventario`: una consulta que
  cruza `INGREDIENTES` (stock_actual < stock_minimo) con `RECETAS` y
  `PRODUCTOS` para obtener productos afectados directamente en SQL/Python
  del lado API.
- `construir_reporte_financiero(db, desde, hasta)` → dict con ventas,
  gastos, ganancia_neta, margen_pct, margen_pct_anterior, variación,
  ranking de margen
- `construir_reporte_inventario(db)` → dict con lista de riesgo

**Nuevo `api/app/services/reportes_export.py`** con:
- `generar_pdf_financiero(datos) -> io.BytesIO` (reportlab, tabla de KPIs +
  tabla de ranking, encabezados en verde marca `#1E3932`/`#00754A`)
- `generar_pdf_inventario(datos) -> io.BytesIO`
- `generar_xlsx_financiero(datos) -> io.BytesIO` (reutiliza estilo actual de
  `openpyxl`, ya con la paleta verde aplicada en la sesión anterior)
- `generar_xlsx_inventario(datos) -> io.BytesIO`

**Modelos nuevos en `api/app/models/reportes.py`:**
- `RankingMargenItem`, `RiesgoInventarioItem`
- `ReporteFinancieroOut` (extiende el actual `ReporteAdmin` con
  `margen_pct`, `margen_pct_anterior`, `variacion_ventas_pct`,
  `variacion_ganancia_pct`, `ranking_margen: list[RankingMargenItem]`)
- `ReporteInventarioOut` (`riesgo: list[RiesgoInventarioItem]`)

`requirements.txt` de `api/` gana `reportlab`.

### Web-admin (Flask) — pura vista + proxy

**`app/api_client.py`** gana:
- `obtener_reporte_financiero(base_url, token, desde, hasta) -> dict`
- `obtener_reporte_inventario(base_url, token) -> dict`
- `descargar_reporte(base_url, token, categoria, formato, params) -> requests.Response`
  (sin parsear el body — se retransmite tal cual)

**`app/blueprints/dashboard.py`**: `index()` ahora solo llama a los dos
`obtener_reporte_*` y pasa los dicts a la plantilla — sin loops, sin cálculo
de margen ni de riesgo.

**`app/blueprints/reportes.py`**: se reduce a 2 rutas de descarga
(`/reportes/financiero/exportar.<formato>`,
`/reportes/inventario/exportar.<formato>`) que llaman a
`descargar_reporte(...)` y retransmiten la respuesta con
`Response(resp.content, mimetype=resp.headers["Content-Type"], headers=...)`.
No hay generación de archivos aquí.

**Se eliminan:**
- `web-admin/app/reportes.py` (lógica movida a la API)
- `web-admin/app/templates/reportes/reporte_pdf.html` (ya no se renderiza
  HTML para PDF; reportlab genera tablas nativas del lado API)
- Import diferido de `weasyprint` y la dependencia en `requirements.txt` /
  `Dockerfile` de `web-admin` (ya no se necesita, se puede quitar
  `libgdk-pixbuf` y compañía del Dockerfile de `web-admin`)

**`templates/dashboard.html`**: se divide en 2 pestañas con Alpine.js
(`x-data="{ tab: 'financiero' }"`), reutilizando `.card`, `.btn`,
`.data-table`, `.badge` ya existentes:
- Tab **Financiero**: las 4 KPI cards actuales + gráfica ventas/gastos +
  tabla de rendimiento de producto + filtro de fechas + botones PDF/XLSX
  propios de esta pestaña.
- Tab **Inventario**: tabla de riesgo de inventario + botones PDF/XLSX
  propios (sin filtro de fechas — el riesgo es "ahora mismo", no
  histórico).

## Manejo de errores

- Si la API responde 401/403 en cualquiera de los 4 endpoints nuevos, Flask
  aplica el mismo patrón ya existente (`@login_required` limpia sesión y
  redirige a `/login`, o página 403).
- Si la descarga falla (>=400), Flask hace `flash("Error al generar
  reporte", "error")` y redirige de vuelta al dashboard (igual que hace
  Macuin en `descargar_reporte`).

## Testing

- **API**: `api/app/tests/test_router_reportes.py` — casos: JSON de
  `/financiero` y `/inventario` con datos sembrados, 403 para rol no
  Administrador, `content-type` correcto en las 4 rutas de descarga, PDF
  válido (`%PDF` magic bytes), XLSX válido.
- **Web-admin**: se actualizan los smoke tests existentes de
  `dashboard`/`reportes` para mockear `obtener_reporte_financiero`,
  `obtener_reporte_inventario` y `descargar_reporte` en vez de las
  funciones viejas; se eliminan los tests de `app/reportes.py` (ya no
  existe) y de `test_reportes_export.py` relacionados a WeasyPrint.
- Verificación manual end-to-end contra Docker (como en la sesión anterior)
  antes de dar el trabajo por terminado: login, ambas pestañas del
  dashboard con datos reales, descarga PDF/XLSX de ambas categorías.

## Riesgos / notas

- Este es un refactor que toca API + Flask simultáneamente; se debe
  mantener ambos lados sincronizados en el mismo PR/commit para no dejar el
  panel roto a medio camino.
- Los tests actuales de `web-admin/tests/test_reportes_export.py` que
  fallan localmente por falta de GTK dejan de existir — este refactor
  resuelve ese problema de raíz al quitar WeasyPrint del proyecto.
