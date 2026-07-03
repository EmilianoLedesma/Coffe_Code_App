# Reportes: filtros y desgloses nuevos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar a `/api/reportes/financiero` los filtros `categoria_id`/`usuario_id` y los desgloses `ventas_por_categoria`/`ventas_por_usuario`/`ventas_por_metodo_pago`; agregar a `/api/reportes/inventario` un rango `desde`/`hasta` y el desglose `ranking_consumo`. Los endpoints PDF/XLSX deben recibir y aplicar los mismos filtros que el JSON (hoy no lo hacen para los parámetros nuevos, así que hay que propagarlos explícitamente en las 3 firmas de router).

**Architecture:** Extender `api/app/services/reportes.py` con funciones puras nuevas (mismo estilo que `calcular_top_productos`/`calcular_ranking_margen`), extender los modelos de respuesta en `api/app/models/reportes.py`, propagar los query params nuevos en `api/app/routers/reportes.py` a las 6 rutas existentes (json+pdf+xlsx × financiero+inventario), y agregar las tablas nuevas a `api/app/services/reportes_export.py`.

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic + reportlab + openpyxl (API), Flask + Jinja2 (web-admin), pytest (ambos lados).

## Global Constraints

- Reportes < 3s para rangos ≤ 6 meses (regla de negocio en `.claude/CLAUDE.md`) — los nuevos joins deben usar agregación en SQL (`GROUP BY`), no traer todo a Python y agrupar en memoria.
- No se reintroduce DOCX ni ninguna librería de export nueva — solo reportlab/openpyxl, ya presentes.
- Todos los campos nuevos son **opcionales** — omitir `categoria_id`/`usuario_id`/`desde`/`hasta` debe devolver exactamente el comportamiento actual (sin filtrar, con el rango default de 30 días donde ya existía).

---

### Task 1: Servicios — desgloses nuevos

**Files:**
- Modify: `api/app/services/reportes.py`
- Test: `api/app/tests/test_reportes_service.py` (si no existe con ese nombre exacto, buscar el archivo de test de servicios de reportes ya existente con `find api/app/tests -iname "*reporte*"` y extenderlo ahí en vez de crear uno nuevo)

**Interfaces:**
- Produces:
  - `calcular_ventas_por_categoria(db, desde, hasta) -> list[dict]` con keys `categoria_id, nombre, total`
  - `calcular_ventas_por_usuario(db, desde, hasta) -> list[dict]` con keys `usuario_id, nombre, total`
  - `calcular_ventas_por_metodo_pago(db, desde, hasta) -> list[dict]` con keys `metodo_pago, total`
  - `calcular_ranking_consumo(db, desde, hasta) -> list[dict]` con keys `ingrediente_id, nombre, unidad, cantidad_consumida`
  - `construir_reporte_financiero(db, desde, hasta, categoria_id=None, usuario_id=None) -> dict` (firma extendida, sigue siendo backward-compatible)
  - `construir_reporte_inventario(db, desde=None, hasta=None) -> dict` (firma extendida)

- [ ] **Step 1: Escribir los tests que deben fallar**

Agregar (usando las fixtures `catalogos`/`db_session`/`mesa_libre` ya existentes en `api/app/tests/conftest.py`, y creando pedidos/tickets/pagos mínimos según el patrón usado en los tests existentes de `test_reportes*.py` — revisar ese archivo primero para copiar el helper de setup de un pedido completo con ticket/pago si ya existe uno):

```python
def test_calcular_ventas_por_metodo_pago_agrupa_correctamente(db_session, catalogos, mesa_libre):
    # crear 2 pedidos con ticket, uno pagado en Efectivo y otro en Tarjeta débito,
    # usando el mismo helper de setup que ya usan los tests de calcular_resumen_caja
    ...
    filas = calcular_ventas_por_metodo_pago(db_session, desde, hasta)
    metodos = {f["metodo_pago"]: f["total"] for f in filas}
    assert metodos[MetodoPagoNombre.EFECTIVO] == Decimal("100.00")
    assert metodos[MetodoPagoNombre.TARJETA_DEBITO] == Decimal("50.00")


def test_calcular_ventas_por_categoria(db_session, catalogos, mesa_libre):
    # 2 productos en categorías distintas, cada uno vendido en un pedido con ticket
    ...
    filas = calcular_ventas_por_categoria(db_session, desde, hasta)
    assert {f["nombre"] for f in filas} == {"Bebidas", "Postres"}


def test_calcular_ranking_consumo_usa_recetas(db_session, catalogos, mesa_libre):
    # 1 producto con receta (2 ingredientes), vendido 3 veces en el rango
    ...
    filas = calcular_ranking_consumo(db_session, desde, hasta)
    # cantidad_consumida = cantidad_requerida_por_receta * cantidad_vendida
    assert filas[0]["cantidad_consumida"] == Decimal("6.00")


def test_construir_reporte_financiero_filtra_por_categoria(db_session, catalogos, mesa_libre):
    ...
    reporte_sin_filtro = construir_reporte_financiero(db_session, desde, hasta)
    reporte_filtrado = construir_reporte_financiero(db_session, desde, hasta, categoria_id=1)
    assert reporte_filtrado["total_ventas"] <= reporte_sin_filtro["total_ventas"]
    assert "ventas_por_categoria" in reporte_sin_filtro
    assert "ventas_por_usuario" in reporte_sin_filtro
    assert "ventas_por_metodo_pago" in reporte_sin_filtro


def test_construir_reporte_inventario_acepta_rango_opcional(db_session, catalogos):
    reporte = construir_reporte_inventario(db_session)
    assert "ranking_consumo" in reporte
    assert reporte["ranking_consumo"] == []
```

Nota importante para quien implemente: antes de escribir el setup de datos de estos tests, leer `api/app/tests/test_reportes_service.py` (o el archivo equivalente) completo para reusar el helper existente que crea pedido+detalle+ticket+pago — no reinventarlo, ya existe uno para los tests de `calcular_resumen_caja`/`calcular_top_productos`.

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_reportes_service.py -v -k "metodo_pago or categoria or consumo"`
Expected: FAIL con `ImportError` o `NameError` (las funciones no existen todavía)

- [ ] **Step 3: Implementar las funciones de servicio**

Agregar a `api/app/services/reportes.py` (después de `calcular_top_productos`):

```python
def calcular_ventas_por_categoria(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            Categoria.id.label("categoria_id"),
            Categoria.nombre.label("nombre"),
            func.coalesce(func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario), 0).label("total"),
        )
        .join(Producto, Producto.id_categoria == Categoria.id)
        .join(DetallePedido, DetallePedido.id_producto == Producto.id)
        .join(Pedido, Pedido.id == DetallePedido.id_pedido)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(Categoria.id, Categoria.nombre)
        .order_by(func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario).desc())
        .all()
    )
    return [
        {"categoria_id": fila.categoria_id, "nombre": fila.nombre, "total": Decimal(fila.total)}
        for fila in filas
    ]


def calcular_ventas_por_usuario(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            Usuario.id.label("usuario_id"),
            Usuario.nombre.label("nombre"),
            func.coalesce(func.sum(Ticket.total), 0).label("total"),
        )
        .join(Pedido, Pedido.id_usuario == Usuario.id)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(Usuario.id, Usuario.nombre)
        .order_by(func.sum(Ticket.total).desc())
        .all()
    )
    return [
        {"usuario_id": fila.usuario_id, "nombre": fila.nombre, "total": Decimal(fila.total)}
        for fila in filas
    ]


def calcular_ventas_por_metodo_pago(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            MetodoPago.nombre.label("metodo_pago"),
            func.coalesce(func.sum(Ticket.total), 0).label("total"),
        )
        .join(Pago, Pago.id_metodo == MetodoPago.id)
        .join(Ticket, Ticket.id == Pago.id_ticket)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(MetodoPago.nombre)
        .order_by(func.sum(Ticket.total).desc())
        .all()
    )
    return [{"metodo_pago": fila.metodo_pago, "total": Decimal(fila.total)} for fila in filas]


def calcular_ranking_consumo(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    filas = (
        db.query(
            Ingrediente.id.label("ingrediente_id"),
            Ingrediente.nombre.label("nombre"),
            Ingrediente.unidad.label("unidad"),
            func.coalesce(func.sum(DetallePedido.cantidad * Receta.cantidad_requerida), 0).label(
                "cantidad_consumida"
            ),
        )
        .join(Receta, Receta.id_ingrediente == Ingrediente.id)
        .join(DetallePedido, DetallePedido.id_producto == Receta.id_producto)
        .join(Pedido, Pedido.id == DetallePedido.id_pedido)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(Ingrediente.id, Ingrediente.nombre, Ingrediente.unidad)
        .order_by(func.sum(DetallePedido.cantidad * Receta.cantidad_requerida).desc())
        .all()
    )
    return [
        {
            "ingrediente_id": fila.ingrediente_id,
            "nombre": fila.nombre,
            "unidad": fila.unidad,
            "cantidad_consumida": Decimal(fila.cantidad_consumida),
        }
        for fila in filas
    ]
```

Agregar los imports que falten al principio del archivo:

```python
from app.data.categorias import Categoria
from app.data.metodos_pago import MetodoPago
from app.data.pagos import Pago
from app.data.usuarios import Usuario
```

Modificar `construir_reporte_financiero` para aceptar los filtros opcionales y agregar los 3 desgloses nuevos al `return`:

```python
def construir_reporte_financiero(
    db: Session,
    desde: datetime,
    hasta: datetime,
    categoria_id: int | None = None,
    usuario_id: int | None = None,
) -> dict:
    reporte_actual = calcular_reporte_admin(db, desde, hasta)
    desde_prev, hasta_prev = periodo_anterior(desde, hasta)
    reporte_anterior = calcular_reporte_admin(db, desde_prev, hasta_prev)

    margen_pct = calcular_margen_pct(reporte_actual["total_ventas"], reporte_actual["ganancia_neta"])
    margen_pct_anterior = calcular_margen_pct(reporte_anterior["total_ventas"], reporte_anterior["ganancia_neta"])
    variacion_ventas_pct = variacion_pct(reporte_actual["total_ventas"], reporte_anterior["total_ventas"])
    variacion_ganancia_pct = variacion_pct(reporte_actual["ganancia_neta"], reporte_anterior["ganancia_neta"])

    ranking_margen = calcular_ranking_margen(db, desde, hasta)
    if categoria_id is not None:
        ranking_margen = [
            fila
            for fila in ranking_margen
            if db.query(Producto.id_categoria).filter(Producto.id == fila["producto_id"]).scalar() == categoria_id
        ]

    ventas_por_usuario = calcular_ventas_por_usuario(db, desde, hasta)
    if usuario_id is not None:
        ventas_por_usuario = [fila for fila in ventas_por_usuario if fila["usuario_id"] == usuario_id]

    return {
        "desde": desde,
        "hasta": hasta,
        "total_ventas": reporte_actual["total_ventas"],
        "total_gastos": reporte_actual["total_gastos"],
        "ganancia_neta": reporte_actual["ganancia_neta"],
        "margen_pct": margen_pct,
        "margen_pct_anterior": margen_pct_anterior,
        "variacion_ventas_pct": variacion_ventas_pct,
        "variacion_ganancia_pct": variacion_ganancia_pct,
        "ranking_margen": ranking_margen,
        "ventas_por_categoria": calcular_ventas_por_categoria(db, desde, hasta),
        "ventas_por_usuario": ventas_por_usuario,
        "ventas_por_metodo_pago": calcular_ventas_por_metodo_pago(db, desde, hasta),
    }


def construir_reporte_inventario(
    db: Session, desde: datetime | None = None, hasta: datetime | None = None
) -> dict:
    resultado = {"riesgo": calcular_riesgo_inventario(db)}
    if desde is not None and hasta is not None:
        resultado["ranking_consumo"] = calcular_ranking_consumo(db, desde, hasta)
    else:
        resultado["ranking_consumo"] = []
    return resultado
```

**Nota sobre `categoria_id`:** el filtro se aplica en Python sobre el resultado ya calculado de `calcular_ranking_margen` (que internamente ya recorre `top_productos`) en vez de parametrizar la query SQL, porque `calcular_ranking_margen`/`calcular_top_productos` no aceptan hoy un filtro de categoría y cambiar su firma interna afectaría a `calcular_reporte_admin` (usado también por `GET /api/reportes` del panel legacy). Es correcto para los volúmenes de datos de esta app (cafetería, no miles de productos); si el performance se vuelve un problema, refactorizar `calcular_top_productos` para aceptar `categoria_id` directamente en el `WHERE` SQL.

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_reportes_service.py -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite de la API**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde

- [ ] **Step 6: Commit**

```bash
git add api/app/services/reportes.py api/app/tests/test_reportes_service.py
git commit -m "feat(api): agregar desgloses por categoria/usuario/metodo de pago y ranking de consumo"
```

---

### Task 2: Modelos de respuesta + router — propagar filtros a JSON y export

**Files:**
- Modify: `api/app/models/reportes.py`
- Modify: `api/app/routers/reportes.py`
- Test: `api/app/tests/test_router_reportes.py` (buscar el nombre real con `find api/app/tests -iname "*router*reporte*"`)

**Interfaces:**
- Consumes: funciones del Task 1.
- Produces: `GET /api/reportes/financiero?categoria_id=&usuario_id=` y sus variantes `/pdf`, `/xlsx` con los mismos params; `GET /api/reportes/inventario?desde=&hasta=` y sus variantes `/pdf`, `/xlsx`.

- [ ] **Step 1: Agregar los modelos de respuesta**

En `api/app/models/reportes.py`, agregar:

```python
class VentaPorCategoriaItem(BaseModel):
    categoria_id: int
    nombre: str
    total: Decimal


class VentaPorUsuarioItem(BaseModel):
    usuario_id: int
    nombre: str
    total: Decimal


class VentaPorMetodoPagoItem(BaseModel):
    metodo_pago: str
    total: Decimal


class RankingConsumoItem(BaseModel):
    ingrediente_id: int
    nombre: str
    unidad: str
    cantidad_consumida: Decimal
```

Y extender `ReporteFinancieroOut`/`ReporteInventarioOut`:

```python
class ReporteFinancieroOut(BaseModel):
    desde: datetime
    hasta: datetime
    total_ventas: Decimal
    total_gastos: Decimal
    ganancia_neta: Decimal
    margen_pct: Decimal
    margen_pct_anterior: Decimal
    variacion_ventas_pct: Decimal | None
    variacion_ganancia_pct: Decimal | None
    ranking_margen: list[RankingMargenItem]
    ventas_por_categoria: list[VentaPorCategoriaItem]
    ventas_por_usuario: list[VentaPorUsuarioItem]
    ventas_por_metodo_pago: list[VentaPorMetodoPagoItem]
```

```python
class ReporteInventarioOut(BaseModel):
    riesgo: list[RiesgoInventarioItem]
    ranking_consumo: list[RankingConsumoItem]
```

- [ ] **Step 2: Escribir los tests que deben fallar**

Agregar al router test existente:

```python
def test_financiero_acepta_categoria_id(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get(
        "/api/reportes/financiero?categoria_id=1", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta.status_code == 200
    assert "ventas_por_categoria" in respuesta.json()


def test_financiero_pdf_acepta_categoria_id(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get(
        "/api/reportes/financiero/pdf?categoria_id=1", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"


def test_inventario_acepta_rango_de_fechas(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get(
        "/api/reportes/inventario?desde=2026-01-01T00:00:00Z&hasta=2026-01-31T23:59:59Z",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 200
    assert "ranking_consumo" in respuesta.json()
```

- [ ] **Step 3: Correr los tests, verificar que fallan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_reportes.py -v -k "categoria_id or rango_de_fechas"`
Expected: FAIL (422 por campos faltantes en el response_model, o params ignorados)

- [ ] **Step 4: Implementar — reescribir `api/app/routers/reportes.py` completo**

```python
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.db import get_db
from app.models.reportes import ReporteFinancieroOut, ReporteInventarioOut
from app.security.auth import require_rol
from app.services.reportes import construir_reporte_financiero, construir_reporte_inventario
from app.services.reportes_export import (
    generar_pdf_financiero,
    generar_pdf_inventario,
    generar_xlsx_financiero,
    generar_xlsx_inventario,
)

router = APIRouter(prefix="/api/reportes", tags=["reportes"])

_solo_admin = require_rol(RolNombre.ADMINISTRADOR)


def _rango_por_defecto(desde: datetime | None, hasta: datetime | None) -> tuple[datetime, datetime]:
    hasta = hasta or datetime.now(timezone.utc)
    desde = desde or (hasta - timedelta(days=30))
    return desde, hasta


@router.get("/financiero", response_model=ReporteFinancieroOut)
def financiero(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    categoria_id: int | None = None,
    usuario_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> dict:
    desde, hasta = _rango_por_defecto(desde, hasta)
    return construir_reporte_financiero(db, desde, hasta, categoria_id=categoria_id, usuario_id=usuario_id)


@router.get("/inventario", response_model=ReporteInventarioOut)
def inventario(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> dict:
    return construir_reporte_inventario(db, desde, hasta)


@router.get("/financiero/pdf")
def financiero_pdf(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    categoria_id: int | None = None,
    usuario_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_financiero(db, desde, hasta, categoria_id=categoria_id, usuario_id=usuario_id)
    buffer = generar_pdf_financiero(datos)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_financiero.pdf"},
    )


@router.get("/financiero/xlsx")
def financiero_xlsx(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    categoria_id: int | None = None,
    usuario_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_financiero(db, desde, hasta, categoria_id=categoria_id, usuario_id=usuario_id)
    buffer = generar_xlsx_financiero(datos)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_financiero.xlsx"},
    )


@router.get("/inventario/pdf")
def inventario_pdf(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    datos = construir_reporte_inventario(db, desde, hasta)
    buffer = generar_pdf_inventario(datos)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_inventario.pdf"},
    )


@router.get("/inventario/xlsx")
def inventario_xlsx(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    datos = construir_reporte_inventario(db, desde, hasta)
    buffer = generar_xlsx_inventario(datos)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_inventario.xlsx"},
    )
```

- [ ] **Step 5: Correr los tests del router, verificar que pasan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_reportes.py -v`
Expected: PASS — Nota: si esto falla porque `reportes_export.py` (Task 3) todavía no acepta las listas nuevas dentro de `datos`, coordinar con esa tarea antes de mergear ambas ramas; los tests de PDF/XLSX de este task solo verifican `status_code`/`content-type`, no el contenido interno, así que no deberían depender del Task 3 para pasar.

- [ ] **Step 6: Commit**

```bash
git add api/app/models/reportes.py api/app/routers/reportes.py api/app/tests/test_router_reportes.py
git commit -m "feat(api): propagar categoria_id/usuario_id/rango de fechas a reportes financiero e inventario"
```

---

### Task 3: Export (PDF/XLSX) — agregar las tablas nuevas

**Files:**
- Modify: `api/app/services/reportes_export.py`
- Test: `api/app/tests/test_reportes_export.py`

**Interfaces:**
- Consumes: `datos["ventas_por_categoria"]`, `datos["ventas_por_usuario"]`, `datos["ventas_por_metodo_pago"]` (financiero); `datos["ranking_consumo"]` (inventario) — producidos por Task 1/2.

- [ ] **Step 1: Escribir los tests que deben fallar**

Agregar a `api/app/tests/test_reportes_export.py`:

```python
def test_generar_pdf_financiero_incluye_metodo_pago():
    datos = {
        "desde": datetime(2026, 1, 1),
        "hasta": datetime(2026, 1, 31),
        "total_ventas": Decimal("100.00"),
        "total_gastos": Decimal("20.00"),
        "ganancia_neta": Decimal("80.00"),
        "margen_pct": Decimal("80.00"),
        "ranking_margen": [],
        "ventas_por_categoria": [],
        "ventas_por_usuario": [],
        "ventas_por_metodo_pago": [{"metodo_pago": "Efectivo", "total": Decimal("100.00")}],
    }
    buffer = generar_pdf_financiero(datos)
    assert buffer.getbuffer().nbytes > 0


def test_generar_xlsx_financiero_incluye_hoja_metodo_pago():
    datos = {
        "desde": datetime(2026, 1, 1),
        "hasta": datetime(2026, 1, 31),
        "total_ventas": Decimal("100.00"),
        "total_gastos": Decimal("20.00"),
        "ganancia_neta": Decimal("80.00"),
        "margen_pct": Decimal("80.00"),
        "ranking_margen": [],
        "ventas_por_categoria": [],
        "ventas_por_usuario": [],
        "ventas_por_metodo_pago": [{"metodo_pago": "Efectivo", "total": Decimal("100.00")}],
    }
    from openpyxl import load_workbook

    buffer = generar_xlsx_financiero(datos)
    libro = load_workbook(buffer)
    assert "Ventas por método de pago" in libro.sheetnames


def test_generar_pdf_inventario_incluye_ranking_consumo():
    datos = {"riesgo": [], "ranking_consumo": [{"nombre": "Café molido", "unidad": "g", "cantidad_consumida": Decimal("500")}]}
    buffer = generar_pdf_inventario(datos)
    assert buffer.getbuffer().nbytes > 0
```

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_reportes_export.py -v -k "metodo_pago or consumo"`
Expected: FAIL con `KeyError` (las funciones actuales no leen esas keys)

- [ ] **Step 3: Implementar**

En `generar_pdf_financiero` (`api/app/services/reportes_export.py`), después del bloque de `ranking_margen`, agregar:

```python
    if datos["ventas_por_categoria"]:
        story.append(Paragraph("Ventas por categoría", h2))
        story.append(
            _tabla(
                [["Categoría", "Total"]]
                + [[fila["nombre"], f"${fila['total']:,.2f}"] for fila in datos["ventas_por_categoria"]]
            )
        )

    if datos["ventas_por_usuario"]:
        story.append(Paragraph("Ventas por mesero/cajero", h2))
        story.append(
            _tabla(
                [["Usuario", "Total"]]
                + [[fila["nombre"], f"${fila['total']:,.2f}"] for fila in datos["ventas_por_usuario"]]
            )
        )

    if datos["ventas_por_metodo_pago"]:
        story.append(Paragraph("Ventas por método de pago", h2))
        story.append(
            _tabla(
                [["Método de pago", "Total"]]
                + [[fila["metodo_pago"], f"${fila['total']:,.2f}"] for fila in datos["ventas_por_metodo_pago"]]
            )
        )
```

En `generar_xlsx_financiero`, después del bloque de `hoja_ranking`, agregar 3 hojas nuevas siguiendo el mismo patrón:

```python
    hoja_categoria = libro.create_sheet("Ventas por categoría")
    hoja_categoria.append(["Categoría", "Total"])
    for celda in hoja_categoria[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ventas_por_categoria"]:
        hoja_categoria.append([fila["nombre"], float(fila["total"])])

    hoja_usuario = libro.create_sheet("Ventas por usuario")
    hoja_usuario.append(["Usuario", "Total"])
    for celda in hoja_usuario[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ventas_por_usuario"]:
        hoja_usuario.append([fila["nombre"], float(fila["total"])])

    hoja_metodo_pago = libro.create_sheet("Ventas por método de pago")
    hoja_metodo_pago.append(["Método de pago", "Total"])
    for celda in hoja_metodo_pago[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ventas_por_metodo_pago"]:
        hoja_metodo_pago.append([fila["metodo_pago"], float(fila["total"])])
```

En `generar_pdf_inventario`, después del bloque `riesgo`, agregar:

```python
    if datos["ranking_consumo"]:
        story.append(Paragraph("Ranking de consumo de ingredientes", h2))
        story.append(
            _tabla(
                [["Ingrediente", "Cantidad consumida"]]
                + [
                    [fila["nombre"], f"{fila['cantidad_consumida']} {fila['unidad']}"]
                    for fila in datos["ranking_consumo"]
                ]
            )
        )
```

En `generar_xlsx_inventario`, después del bloque de `hoja`, agregar:

```python
    hoja_consumo = libro.create_sheet("Ranking de consumo")
    hoja_consumo.append(["Ingrediente", "Unidad", "Cantidad consumida"])
    for celda in hoja_consumo[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ranking_consumo"]:
        hoja_consumo.append([fila["nombre"], fila["unidad"], float(fila["cantidad_consumida"])])
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_reportes_export.py -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite de la API**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde

- [ ] **Step 6: Commit**

```bash
git add api/app/services/reportes_export.py api/app/tests/test_reportes_export.py
git commit -m "feat(api): agregar tablas de metodo de pago, categoria, usuario y consumo a PDF/XLSX"
```

---

### Task 4: Dashboard web-admin consume los desgloses nuevos

**Files:**
- Modify: `web-admin/app/templates/dashboard.html`
- Test: `web-admin/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `financiero.ventas_por_categoria`, `financiero.ventas_por_usuario`, `financiero.ventas_por_metodo_pago`, `inventario.ranking_consumo` (ya vienen en el JSON gracias a Task 2, sin cambios necesarios en `web-admin/app/api_client.py` ni en `web-admin/app/blueprints/dashboard.py` porque ambos ya pasan el dict completo de la API al template).

- [ ] **Step 1: Escribir el test que debe fallar**

Agregar a `web-admin/tests/test_dashboard.py` (revisar primero cómo el archivo mockea `GET /api/reportes/financiero` para reusar el mismo estilo):

```python
@responses.activate
def test_dashboard_muestra_ventas_por_metodo_pago(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero",
        json={
            "desde": "2026-01-01T00:00:00", "hasta": "2026-01-31T00:00:00",
            "total_ventas": "100.00", "total_gastos": "20.00", "ganancia_neta": "80.00",
            "margen_pct": "80.00", "margen_pct_anterior": "70.00",
            "variacion_ventas_pct": None, "variacion_ganancia_pct": None,
            "ranking_margen": [],
            "ventas_por_categoria": [],
            "ventas_por_usuario": [],
            "ventas_por_metodo_pago": [{"metodo_pago": "Efectivo", "total": "100.00"}],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario",
        json={"riesgo": [], "ranking_consumo": []},
        status=200,
    )

    respuesta = client.get("/")

    assert respuesta.status_code == 200
    assert b"Efectivo" in respuesta.data
```

- [ ] **Step 2: Correr el test, verificar que falla**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_dashboard.py -v -k metodo_pago`
Expected: FAIL (el template no renderiza esa sección todavía)

- [ ] **Step 3: Implementar**

En `web-admin/app/templates/dashboard.html`, agregar una nueva sección justo después del `</div>` que cierra el bloque de "Rendimiento de producto" (línea 90) y antes del `</div>` que cierra `x-show="tab === 'financiero'"` (línea 91):

```html
    <div class="grid grid-cols-3 gap-6 mt-8">
      <div class="card overflow-hidden">
        <div class="p-5 pb-0"><h2 class="text-lg font-semibold mb-3">Por categoría</h2></div>
        <table class="data-table">
          <thead><tr><th>Categoría</th><th>Total</th></tr></thead>
          <tbody>
            {% for fila in financiero.ventas_por_categoria %}
            <tr><td>{{ fila.nombre }}</td><td>${{ "%.2f"|format(fila.total|float) }}</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      <div class="card overflow-hidden">
        <div class="p-5 pb-0"><h2 class="text-lg font-semibold mb-3">Por mesero/cajero</h2></div>
        <table class="data-table">
          <thead><tr><th>Usuario</th><th>Total</th></tr></thead>
          <tbody>
            {% for fila in financiero.ventas_por_usuario %}
            <tr><td>{{ fila.nombre }}</td><td>${{ "%.2f"|format(fila.total|float) }}</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      <div class="card overflow-hidden">
        <div class="p-5 pb-0"><h2 class="text-lg font-semibold mb-3">Por método de pago</h2></div>
        <table class="data-table">
          <thead><tr><th>Método</th><th>Total</th></tr></thead>
          <tbody>
            {% for fila in financiero.ventas_por_metodo_pago %}
            <tr><td>{{ fila.metodo_pago }}</td><td>${{ "%.2f"|format(fila.total|float) }}</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
```

Y en la sección de inventario (después del bloque `{% if inventario.riesgo %}...{% endif %}`, antes de la línea 126 `</div>`), agregar:

```html
    <div class="card overflow-hidden mt-6">
      <div class="p-5 pb-0"><h2 class="text-lg font-semibold mb-3">Ranking de consumo de ingredientes</h2></div>
      {% if inventario.ranking_consumo %}
      <table class="data-table">
        <thead><tr><th>Ingrediente</th><th>Cantidad consumida</th></tr></thead>
        <tbody>
          {% for fila in inventario.ranking_consumo %}
          <tr><td>{{ fila.nombre }}</td><td>{{ fila.cantidad_consumida }} {{ fila.unidad }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
      <p class="text-black/58 text-sm p-5">Sin datos de consumo en el periodo seleccionado.</p>
      {% endif %}
    </div>
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite de web-admin**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde

- [ ] **Step 6: Commit**

```bash
git add web-admin/app/templates/dashboard.html web-admin/tests/test_dashboard.py
git commit -m "feat(web-admin): mostrar desgloses por categoria, usuario, metodo de pago y consumo"
```

---

### Task 5: Postman

**Files:**
- Modify: `postman/coffee-code.postman_collection.json`

- [ ] **Step 1: Actualizar las requests existentes de "05 - Admin - Reportes"** agregando ejemplos de query params nuevos (`?categoria_id=1&usuario_id=1` en financiero, `?desde=&hasta=` en inventario) como variantes documentadas — no hace falta duplicar cada request, basta con anotar los params opcionales en la request ya existente (Postman permite params deshabilitados por default).

- [ ] **Step 2: Validar JSON**

Run: `python -c "import json; json.load(open('postman/coffee-code.postman_collection.json', encoding='utf-8'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add postman/coffee-code.postman_collection.json
git commit -m "docs(postman): documentar filtros nuevos de reportes financiero/inventario"
```
