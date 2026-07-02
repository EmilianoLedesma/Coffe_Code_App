# Panel Web Admin (Flask) — Diseño

**Fecha:** 2026-07-02
**Estado:** Aprobado, pendiente de plan de implementación

## Contexto

Coffee Code ya tiene la API central (FastAPI) funcional y corriendo en Docker
(`http://localhost:8010` desde el host, `http://coffee_code_api:8000` entre
contenedores). Falta el componente **Panel Admin** descrito en
`.claude/CLAUDE.md`: gestión de usuarios/roles + estadísticas, exclusivo para
el rol `Administrador`, consumiendo la API sin lógica de negocio propia ni
acceso directo a la base de datos.

## Objetivo

Construir `web-admin/` como una app Flask profesional, visualmente
impresionante (identidad de marca Coffee Code: paleta café cálida), que:

1. Autentica contra `POST /auth/login` y solo permite entrar a usuarios con
   rol `Administrador`.
2. Gestiona usuarios/roles, catálogo (productos, ingredientes, recetas).
3. Muestra un dashboard de reportes **accionables** (no vanity metrics).
4. Exporta reportes a PDF y XLSX.
5. Corre como servicio Docker adicional, junto a `coffee_code_db` y
   `coffee_code_api`.

## Fuera de alcance

- Ninguna lógica de negocio nueva: Flask solo lee/agrega datos ya expuestos
  por la API (o cruza varias respuestas de la API en memoria — nunca toca
  Postgres directamente ni decide transiciones de estado).
- No se toca el móvil (React Native) en este trabajo.
- No se usa Three.js — se descartó a favor de un dashboard 2D limpio con
  Chart.js, priorizando claridad de datos sobre efectos visuales.

## Arquitectura

- **Stack**: Flask 3 + Jinja2 + Tailwind CSS + Alpine.js (interactividad de
  modales/tabs sin SPA) + Chart.js (gráficas) + WeasyPrint (PDF) + openpyxl
  (XLSX).
- **Estructura** (`web-admin/`):
  ```
  web-admin/
  ├── app/
  │   ├── __init__.py          # app factory, registra blueprints
  │   ├── config.py            # Settings vía pydantic-settings o dataclass + .env
  │   ├── api_client.py        # wrapper HTTP hacia la API central
  │   ├── auth.py               # login_required decorator, manejo de sesión
  │   ├── blueprints/
  │   │   ├── auth.py           # /login, /logout
  │   │   ├── dashboard.py      # / (reportes accionables)
  │   │   ├── usuarios.py       # /usuarios CRUD
  │   │   ├── productos.py      # /productos CRUD
  │   │   ├── ingredientes.py   # /ingredientes CRUD + stock
  │   │   ├── recetas.py        # /recetas
  │   │   └── reportes.py       # /reportes/exportar.pdf, /reportes/exportar.xlsx
  │   ├── templates/
  │   │   ├── base.html         # layout: sidebar + topbar
  │   │   ├── login.html
  │   │   ├── dashboard.html
  │   │   ├── usuarios.html
  │   │   ├── productos.html
  │   │   ├── ingredientes.html
  │   │   ├── recetas.html
  │   │   └── reportes/
  │   │       └── reporte_pdf.html   # plantilla base para WeasyPrint
  │   └── static/
  │       ├── css/ (Tailwind compilado)
  │       └── js/ (Alpine.js, Chart.js config/theming)
  ├── tests/                    # smoke tests de rutas con api_client mockeado
  ├── Dockerfile
  ├── requirements.txt
  ├── .env.example
  └── .env
  ```
- **Sesión / Auth**: `POST /auth/login` de la API retorna `{access_token, rol}`.
  Flask valida `rol == "Administrador"`; si no, rechaza con mensaje claro. El
  JWT se guarda en `flask.session` (cookie firmada con `SECRET_KEY` propio,
  `HttpOnly`, `SameSite=Lax`). Decorador `@login_required` en todas las vistas
  salvo `/login`. `api_client` inyecta `Authorization: Bearer {token}` en cada
  llamada; si la API responde 401, se limpia la sesión y se redirige a
  `/login`.
- **api_client.py**: funciones delgadas por recurso (`listar_usuarios()`,
  `crear_usuario(payload)`, `listar_productos()`, `obtener_reporte(desde,
  hasta)`, etc.), todas usando `requests.Session` con timeout y manejo de
  errores HTTP → excepciones propias (`ApiError`) que las vistas traducen a
  `flash()`.
- **Docker**: nuevo servicio `coffee_code_web` en `docker-compose.yml`:
  ```yaml
  coffee_code_web:
    build: ./web-admin
    container_name: coffee_code_web
    restart: unless-stopped
    env_file: ./web-admin/.env
    environment:
      COFFEE_API_URL: http://coffee_code_api:8000
    ports:
      - "8020:5000"
    depends_on:
      - coffee_code_api
    volumes:
      - ./web-admin:/app
  ```

## Módulos y páginas

| Módulo | Ruta | API consumida | Contenido |
|---|---|---|---|
| Login | `/login` | `POST /auth/login` | Form correo/password, valida rol Administrador |
| Dashboard | `/` | `GET /api/reportes`, `GET /caja/resumen`, `GET /productos`, `GET /ingredientes`, recetas | Ver sección "Reportes accionables" |
| Usuarios | `/usuarios` | `GET/POST/PUT /api/usuarios` | Tabla + modal CRUD, filtro por rol/activo, activar/desactivar, cambio de rol |
| Productos | `/productos` | `GET/POST/PUT/DELETE /productos` | Tabla por categoría, modal CRUD, toggle disponible/activo |
| Ingredientes | `/ingredientes` | `GET/POST /ingredientes`, `PUT /ingredientes/{id}/stock` | Tabla con indicador de stock bajo, modal CRUD, ajuste rápido de stock |
| Recetas | `/recetas` | `POST /producto_ingrediente` + lectura vía producto | Vista por producto: ingredientes asociados + cantidad, alta de receta |

Todas las tablas con búsqueda/orden client-side vía Alpine.js (sin librería
de tablas pesada). Layout compartido: sidebar fija con branding + navegación,
topbar con nombre del admin logueado + logout.

## Reportes accionables (Dashboard)

Nada de conteos triviales ("productos totales", "productos con leche"). Tres
bloques, todos calculados a partir de datos ya expuestos por la API
(agregación en Flask, sin lógica de negocio nueva):

1. **Salud financiera del periodo** — ventas, gastos, ganancia neta y
   **margen %** (`ganancia_neta / total_ventas`), comparado contra el
   periodo anterior equivalente (mismo número de días, desplazado hacia
   atrás) para mostrar tendencia ↑/↓, no solo un número aislado.
2. **Rendimiento de producto** — top productos por ingresos (ya lo da
   `/api/reportes`) **más** un ranking por margen unitario, calculado
   cruzando `precio_venta` del producto con el costo de su receta
   (`Σ cantidad_requerida × costo_unitario` de cada ingrediente en
   `RECETAS`). Expone qué se vende mucho pero deja poco margen vs. qué
   convendría empujar más.
3. **Riesgo de inventario accionable** — ingredientes con
   `stock_actual < stock_minimo` ahora mismo, mostrando cuánto falta y a
   qué productos bloquea (vía recetas). Complementado con gasto en compras
   del periodo (vía `/api/reportes` o `/caja/resumen`) para detectar
   sobrecompra.

Estos tres bloques alimentan tanto el dashboard interactivo (Chart.js) como
la exportación PDF/XLSX — mismo cálculo, misma fuente de verdad.

## Exportación PDF/XLSX

- `GET /reportes/exportar.pdf?desde=&hasta=`: renderiza
  `templates/reportes/reporte_pdf.html` (tabla + resumen, sin JS, estilos
  inline/CSS simple) y lo convierte con WeasyPrint. Incluye branding
  (colores, nombre "Coffee Code", rango de fechas).
- `GET /reportes/exportar.xlsx?desde=&hasta=`: arma un workbook con openpyxl,
  una hoja por bloque (Resumen financiero, Rendimiento de producto, Riesgo de
  inventario), encabezados con color de marca.

## Sistema visual

- **Paleta** (heredada de la identidad ya usada en el README): fondo crema
  `#F5E6D3`, texto café oscuro `#3B2412`, acentos `#6F4E37` (café) y
  `#A87C5F` (caramelo); verde/rojo semánticos discretos para tendencias y
  alertas de stock.
- **Tipografía**: sans serif limpia para UI (Inter), toque serif/display
  solo en el título de marca en la sidebar.
- **Componentes**: cards con sombra suave y bordes redondeados grandes,
  sidebar fija café oscuro con íconos, tablas con hover sutil y zebra
  striping ligero, badges semánticos (activo/inactivo, stock bajo),
  gráficas Chart.js con theming de marca (no colores default de librería).
- **Micro-interacción**: transiciones CSS suaves en modales/hover, skeleton
  loaders simples durante carga. Sin Three.js ni efectos 3D.

## Manejo de errores

- Errores de red/timeout hacia la API → página de error genérica con opción
  de reintentar.
- 401 de la API → limpiar sesión, redirigir a `/login` con mensaje.
- 403 (rol no autorizado, ya sea al hacer login con un rol distinto de
  Administrador, o si la API rechaza una acción) → página 403 clara.
- Errores de validación (422) → `flash()` con el detalle devuelto por la API,
  el formulario conserva los valores ingresados.

## Testing

- Smoke tests de rutas Flask con `api_client` mockeado (no se levanta la API
  real en tests unitarios): login exitoso/fallido, gating por rol, cada
  blueprint responde 200 autenticado y 302 sin sesión.
- Verificación manual end-to-end contra la API real levantada en Docker
  (login real, CRUD real, export real) antes de dar el trabajo por
  terminado.

## Plan de implementación

Se detalla en un documento de plan separado (`writing-plans`), generado tras
la aprobación de este spec.
