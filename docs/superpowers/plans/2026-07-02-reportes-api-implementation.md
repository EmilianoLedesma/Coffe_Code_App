# Reportes movidos a la API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mover el cálculo de reportes (financiero + riesgo de inventario) y la generación de PDF/XLSX de `web-admin` (Flask) a la API central (FastAPI), y dividir el dashboard en 2 pestañas (Financiero / Inventario), siguiendo el patrón de un proyecto de referencia donde Flask solo consume JSON y hace proxy de descargas binarias.

**Architecture:** Nuevo router `api/app/routers/reportes.py` bajo `/api/reportes/*` (JWT + rol Administrador) expone JSON (`/financiero`, `/inventario`) y descarga (`/financiero/pdf`, `/financiero/xlsx`, `/inventario/pdf`, `/inventario/xlsx`, generadas con reportlab + openpyxl). `web-admin` pierde toda lógica de negocio: `app/reportes.py` se elimina, `blueprints/dashboard.py` solo hace fetch de los 2 endpoints JSON, `blueprints/reportes.py` solo hace proxy de bytes.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, reportlab, openpyxl, Flask, Jinja2, Alpine.js, pytest, responses (mock HTTP en tests de Flask).

## Global Constraints

- Toda la lógica de negocio vive en FastAPI; Flask y React Native son solo clientes (regla de `.claude/CLAUDE.md`).
- Autenticación: JWT Bearer + `require_rol(RolNombre.ADMINISTRADOR)` en los endpoints nuevos — no se introduce HTTPBasic ni otro esquema.
- Solo 2 formatos de exportación: PDF y XLSX. No se agrega DOCX.
- No se toca ni se elimina el endpoint existente `GET /api/reportes` de `api/app/routers/admin.py` — sigue siendo parte del contrato documentado en `.claude/CLAUDE.md`, aunque Flask deje de llamarlo directamente.
- Español para nombres de tablas/campos/mensajes de error; inglés aceptable en nombres internos de variables/funciones si aplica, pero se sigue el estilo ya usado en el proyecto (funciones y variables en español).
- Paleta visual: reutilizar los colores ya aplicados del sistema Starbucks-inspirado (`.claude/DESING.md`) — House Green `#1E3932`, Green Accent `#00754A` — en los reportes PDF/XLSX generados por la API.
- Cada endpoint nuevo se agrega a la colección de Postman (`postman/coffee-code.postman_collection.json`) — igual que el resto del proyecto (aunque los reportes de Admin normalmente se prueban vía la web, se agregan las 6 rutas nuevas por completitud, siguiendo la convención de "cada endpoint nuevo debe acompañarse de su request de Postman").

---

### Task 1: Modelos y lógica de negocio de reportes en la API

**Files:**
- Modify: `api/app/models/reportes.py`
- Modify: `api/app/services/reportes.py`
- Test: `api/app/tests/test_services_reportes.py` (crear)

**Interfaces:**
- Consumes: `api.app.services.reportes.calcular_reporte_admin(db, desde, hasta)` (ya existe, sin cambios), modelos ORM `Receta`, `Ingrediente`, `Producto` (`api/app/data/recetas.py`, `api/app/data/ingredientes.py`, `api/app/data/productos.py`).
- Produces (usados por Tasks 2 y 3):
  - `periodo_anterior(desde: datetime, hasta: datetime) -> tuple[datetime, datetime]`
  - `calcular_margen_pct(total_ventas, ganancia_neta) -> Decimal`
  - `variacion_pct(actual, anterior) -> Decimal | None`
  - `costo_receta_producto(db: Session, producto_id: int) -> Decimal`
  - `calcular_ranking_margen(db: Session, desde: datetime, hasta: datetime) -> list[dict]`
  - `calcular_riesgo_inventario(db: Session) -> list[dict]`
  - `construir_reporte_financiero(db: Session, desde: datetime, hasta: datetime) -> dict`
  - `construir_reporte_inventario(db: Session) -> dict`
  - Modelos pydantic: `RankingMargenItem`, `ReporteFinancieroOut`, `RiesgoInventarioItem`, `ReporteInventarioOut` (en `api/app/models/reportes.py`)

- [ ] **Step 1: Escribir el test que falla para `costo_receta_producto`**

Crear `api/app/tests/test_services_reportes.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.constants import EstatusCocinaNombre, EstatusPedidoNombre
from app.data.categorias import Categoria
from app.data.detalle_pedidos import DetallePedido
from app.data.ingredientes import Ingrediente
from app.data.pedidos import Pedido
from app.data.productos import Producto
from app.data.recetas import Receta
from app.data.tickets import Ticket
from app.services.reportes import (
    calcular_margen_pct,
    calcular_riesgo_inventario,
    calcular_ranking_margen,
    construir_reporte_financiero,
    construir_reporte_inventario,
    costo_receta_producto,
    periodo_anterior,
    variacion_pct,
)


@pytest.fixture()
def categoria(db_session):
    cat = Categoria(nombre="Bebidas calientes", activo=True)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def producto_con_receta(db_session, categoria):
    producto = Producto(
        nombre="Latte",
        precio_venta=Decimal("55.00"),
        disponible=True,
        activo=True,
        id_categoria=categoria.id,
    )
    ingrediente = Ingrediente(
        nombre="Leche entera",
        unidad="ml",
        stock_actual=Decimal("5000"),
        stock_minimo=Decimal("1000"),
        costo_unitario=Decimal("0.02"),
        activo=True,
    )
    db_session.add_all([producto, ingrediente])
    db_session.flush()

    receta = Receta(id_producto=producto.id, id_ingrediente=ingrediente.id, cantidad_requerida=Decimal("200"))
    db_session.add(receta)
    db_session.flush()
    return producto, ingrediente


def test_costo_receta_producto_suma_cantidad_por_costo_unitario(db_session, producto_con_receta):
    producto, _ = producto_con_receta
    resultado = costo_receta_producto(db_session, producto.id)
    assert resultado == Decimal("4.00")  # 200 ml * 0.02


def test_costo_receta_producto_sin_receta_da_cero(db_session, categoria):
    producto = Producto(
        nombre="Agua embotellada",
        precio_venta=Decimal("15.00"),
        disponible=True,
        activo=True,
        id_categoria=categoria.id,
    )
    db_session.add(producto)
    db_session.flush()
    assert costo_receta_producto(db_session, producto.id) == Decimal("0")


def test_periodo_anterior_mismo_numero_de_dias():
    desde = datetime(2026, 6, 1, tzinfo=timezone.utc)
    hasta = datetime(2026, 6, 10, tzinfo=timezone.utc)
    desde_prev, hasta_prev = periodo_anterior(desde, hasta)
    assert hasta_prev == desde
    assert (hasta - desde) == (hasta_prev - desde_prev)


def test_calcular_margen_pct():
    assert calcular_margen_pct(Decimal("1000"), Decimal("250")) == Decimal("25.00")


def test_variacion_pct_sin_periodo_anterior():
    assert variacion_pct(Decimal("120"), Decimal("0")) is None


def test_calcular_riesgo_inventario_solo_incluye_bajo_stock_minimo(db_session, producto_con_receta):
    producto, ingrediente = producto_con_receta
    ingrediente.stock_actual = Decimal("500")
    db_session.flush()

    resultado = calcular_riesgo_inventario(db_session)

    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Leche entera"
    assert resultado[0]["falta"] == Decimal("500")
    assert resultado[0]["costo_reposicion"] == Decimal("10.00")
    assert resultado[0]["productos_afectados"] == ["Latte"]


def test_calcular_riesgo_inventario_vacio_si_stock_suficiente(db_session, producto_con_receta):
    resultado = calcular_riesgo_inventario(db_session)
    assert resultado == []


def _crear_venta(db_session, catalogos, mesa_libre, usuario_mesero, producto, cantidad, precio_unitario, fecha):
    pedido = Pedido(
        fecha=fecha,
        id_mesa=mesa_libre.id,
        id_usuario=usuario_mesero.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.ENTREGADO].id,
    )
    db_session.add(pedido)
    db_session.flush()

    detalle = DetallePedido(
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        id_producto=producto.id,
        id_pedido=pedido.id,
        id_estatus=catalogos["estatus_cocina"][EstatusCocinaNombre.LISTO].id,
    )
    db_session.add(detalle)
    db_session.flush()

    subtotal = precio_unitario * cantidad
    ticket = Ticket(
        subtotal=subtotal,
        iva=(subtotal * Decimal("0.16")).quantize(Decimal("0.01")),
        total=(subtotal * Decimal("1.16")).quantize(Decimal("0.01")),
        fecha_emision=fecha,
        id_pedido=pedido.id,
        id_usuario=usuario_mesero.id,
    )
    db_session.add(ticket)
    db_session.flush()
    return ticket


def test_calcular_ranking_margen(db_session, catalogos, mesa_libre, usuario_mesero, producto_con_receta):
    producto, _ = producto_con_receta
    fecha = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _crear_venta(db_session, catalogos, mesa_libre, usuario_mesero, producto, cantidad=10, precio_unitario=Decimal("55.00"), fecha=fecha)

    desde = datetime(2026, 6, 1, tzinfo=timezone.utc)
    hasta = datetime(2026, 6, 30, tzinfo=timezone.utc)
    resultado = calcular_ranking_margen(db_session, desde, hasta)

    assert len(resultado) == 1
    fila = resultado[0]
    assert fila["nombre"] == "Latte"
    assert fila["ingresos"] == Decimal("550.00")
    assert fila["costo_total"] == Decimal("40.00")  # 10 * 4.00
    assert fila["margen"] == Decimal("510.00")


def test_construir_reporte_financiero(db_session, catalogos, mesa_libre, usuario_mesero, producto_con_receta):
    producto, _ = producto_con_receta
    fecha = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _crear_venta(db_session, catalogos, mesa_libre, usuario_mesero, producto, cantidad=10, precio_unitario=Decimal("55.00"), fecha=fecha)

    desde = datetime(2026, 6, 1, tzinfo=timezone.utc)
    hasta = datetime(2026, 6, 30, tzinfo=timezone.utc)
    resultado = construir_reporte_financiero(db_session, desde, hasta)

    assert resultado["total_ventas"] == Decimal("638.00")  # Ticket.total incluye IVA (550.00 subtotal * 1.16)
    assert resultado["margen_pct"] > Decimal("0")
    assert len(resultado["ranking_margen"]) == 1
    assert resultado["variacion_ventas_pct"] is None  # sin ventas en periodo anterior


def test_construir_reporte_inventario_vacio(db_session, catalogos):
    resultado = construir_reporte_inventario(db_session)
    assert resultado == {"riesgo": []}
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_services_reportes.py -v`
Expected: FAIL con `ImportError: cannot import name 'costo_receta_producto' from 'app.services.reportes'` (las funciones aún no existen).

- [ ] **Step 3: Extender `api/app/models/reportes.py`**

Reemplazar el contenido completo del archivo con:

```python
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TopProductoOut(BaseModel):
    producto_id: int
    nombre: str
    cantidad_vendida: int
    ingresos: Decimal


class ReporteAdmin(BaseModel):
    desde: datetime
    hasta: datetime
    total_ventas: Decimal
    total_gastos: Decimal
    ganancia_neta: Decimal
    top_productos: list[TopProductoOut]


class RankingMargenItem(BaseModel):
    producto_id: int
    nombre: str
    ingresos: Decimal
    costo_total: Decimal
    margen: Decimal
    margen_pct: Decimal


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


class RiesgoInventarioItem(BaseModel):
    id: int
    nombre: str
    unidad: str
    stock_actual: Decimal
    stock_minimo: Decimal
    falta: Decimal
    costo_reposicion: Decimal
    productos_afectados: list[str]


class ReporteInventarioOut(BaseModel):
    riesgo: list[RiesgoInventarioItem]
```

- [ ] **Step 4: Extender `api/app/services/reportes.py`**

Reemplazar el contenido completo del archivo con:

```python
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data.detalle_pedidos import DetallePedido
from app.data.gastos import Gasto
from app.data.ingredientes import Ingrediente
from app.data.pedidos import Pedido
from app.data.productos import Producto
from app.data.recetas import Receta
from app.data.tickets import Ticket


def calcular_resumen_caja(db: Session, desde: datetime, hasta: datetime) -> dict:
    total_ventas = (
        db.query(func.coalesce(func.sum(Ticket.total), 0))
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .scalar()
    )
    total_gastos = (
        db.query(func.coalesce(func.sum(Gasto.monto), 0))
        .filter(Gasto.fecha_gasto >= desde, Gasto.fecha_gasto <= hasta)
        .scalar()
    )
    total_ventas = Decimal(total_ventas)
    total_gastos = Decimal(total_gastos)

    return {
        "desde": desde,
        "hasta": hasta,
        "total_ventas": total_ventas,
        "total_gastos": total_gastos,
        "ganancia_neta": total_ventas - total_gastos,
    }


def calcular_top_productos(db: Session, desde: datetime, hasta: datetime, limite: int = 5) -> list[dict]:
    filas = (
        db.query(
            Producto.id.label("producto_id"),
            Producto.nombre.label("nombre"),
            func.coalesce(func.sum(DetallePedido.cantidad), 0).label("cantidad_vendida"),
            func.coalesce(func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario), 0).label(
                "ingresos"
            ),
        )
        .join(DetallePedido, DetallePedido.id_producto == Producto.id)
        .join(Pedido, Pedido.id == DetallePedido.id_pedido)
        .join(Ticket, Ticket.id_pedido == Pedido.id)
        .filter(Ticket.fecha_emision >= desde, Ticket.fecha_emision <= hasta)
        .group_by(Producto.id, Producto.nombre)
        .order_by(func.sum(DetallePedido.cantidad).desc())
        .limit(limite)
        .all()
    )
    return [
        {
            "producto_id": fila.producto_id,
            "nombre": fila.nombre,
            "cantidad_vendida": int(fila.cantidad_vendida),
            "ingresos": Decimal(fila.ingresos),
        }
        for fila in filas
    ]


def calcular_reporte_admin(db: Session, desde: datetime, hasta: datetime) -> dict:
    resumen = calcular_resumen_caja(db, desde, hasta)
    resumen["top_productos"] = calcular_top_productos(db, desde, hasta)
    return resumen


def periodo_anterior(desde: datetime, hasta: datetime) -> tuple[datetime, datetime]:
    duracion = hasta - desde
    return desde - duracion, desde


def _dec(valor) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def calcular_margen_pct(total_ventas, ganancia_neta) -> Decimal:
    total_ventas = _dec(total_ventas)
    ganancia_neta = _dec(ganancia_neta)
    if total_ventas == 0:
        return Decimal("0")
    return (ganancia_neta / total_ventas * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def variacion_pct(actual, anterior) -> Decimal | None:
    actual = _dec(actual)
    anterior = _dec(anterior)
    if anterior == 0:
        return None
    return ((actual - anterior) / anterior * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def costo_receta_producto(db: Session, producto_id: int) -> Decimal:
    filas = (
        db.query(Receta.cantidad_requerida, Ingrediente.costo_unitario)
        .join(Ingrediente, Receta.id_ingrediente == Ingrediente.id)
        .filter(Receta.id_producto == producto_id)
        .all()
    )
    total = Decimal("0")
    for cantidad_requerida, costo_unitario in filas:
        total += _dec(cantidad_requerida) * _dec(costo_unitario)
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_ranking_margen(db: Session, desde: datetime, hasta: datetime) -> list[dict]:
    top_productos = calcular_top_productos(db, desde, hasta)
    filas = []
    for producto in top_productos:
        cantidad = producto["cantidad_vendida"] or 1
        ingresos = producto["ingresos"]
        costo_unitario_total = costo_receta_producto(db, producto["producto_id"])
        costo_total = (costo_unitario_total * cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        margen = ingresos - costo_total
        margen_pct = calcular_margen_pct(ingresos, margen)
        filas.append(
            {
                "producto_id": producto["producto_id"],
                "nombre": producto["nombre"],
                "ingresos": ingresos,
                "costo_total": costo_total,
                "margen": margen,
                "margen_pct": margen_pct,
            }
        )
    return sorted(filas, key=lambda fila: fila["margen_pct"])


def calcular_riesgo_inventario(db: Session) -> list[dict]:
    ingredientes_bajo_stock = (
        db.query(Ingrediente)
        .filter(Ingrediente.activo.is_(True), Ingrediente.stock_actual < Ingrediente.stock_minimo)
        .all()
    )
    filas = []
    for ingrediente in ingredientes_bajo_stock:
        productos_afectados = (
            db.query(Producto.nombre)
            .join(Receta, Receta.id_producto == Producto.id)
            .filter(Receta.id_ingrediente == ingrediente.id)
            .order_by(Producto.nombre)
            .all()
        )
        nombres = [nombre for (nombre,) in productos_afectados]
        falta = ingrediente.stock_minimo - ingrediente.stock_actual
        costo_reposicion = (falta * ingrediente.costo_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        filas.append(
            {
                "id": ingrediente.id,
                "nombre": ingrediente.nombre,
                "unidad": ingrediente.unidad,
                "stock_actual": ingrediente.stock_actual,
                "stock_minimo": ingrediente.stock_minimo,
                "falta": falta,
                "costo_reposicion": costo_reposicion,
                "productos_afectados": nombres,
            }
        )
    return sorted(filas, key=lambda fila: fila["falta"], reverse=True)


def construir_reporte_financiero(db: Session, desde: datetime, hasta: datetime) -> dict:
    reporte_actual = calcular_reporte_admin(db, desde, hasta)
    desde_prev, hasta_prev = periodo_anterior(desde, hasta)
    reporte_anterior = calcular_reporte_admin(db, desde_prev, hasta_prev)

    margen_pct = calcular_margen_pct(reporte_actual["total_ventas"], reporte_actual["ganancia_neta"])
    margen_pct_anterior = calcular_margen_pct(reporte_anterior["total_ventas"], reporte_anterior["ganancia_neta"])
    variacion_ventas_pct = variacion_pct(reporte_actual["total_ventas"], reporte_anterior["total_ventas"])
    variacion_ganancia_pct = variacion_pct(reporte_actual["ganancia_neta"], reporte_anterior["ganancia_neta"])
    ranking_margen = calcular_ranking_margen(db, desde, hasta)

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
    }


def construir_reporte_inventario(db: Session) -> dict:
    return {"riesgo": calcular_riesgo_inventario(db)}
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_services_reportes.py -v`
Expected: PASS (10 tests)

- [ ] **Step 6: Commit**

```bash
git add api/app/models/reportes.py api/app/services/reportes.py api/app/tests/test_services_reportes.py
git commit -m "feat(api): mover calculo de margen y riesgo de inventario a services/reportes"
```

---

### Task 2: Generadores de archivo (PDF con reportlab, XLSX con openpyxl)

**Files:**
- Create: `api/app/services/reportes_export.py`
- Modify: `api/requirements.txt`
- Test: `api/app/tests/test_reportes_export.py` (crear)

**Interfaces:**
- Consumes: dicts producidos por `construir_reporte_financiero()` / `construir_reporte_inventario()` (Task 1).
- Produces (usados por Task 3): `generar_pdf_financiero(datos: dict) -> io.BytesIO`, `generar_xlsx_financiero(datos: dict) -> io.BytesIO`, `generar_pdf_inventario(datos: dict) -> io.BytesIO`, `generar_xlsx_inventario(datos: dict) -> io.BytesIO`.

- [ ] **Step 1: Escribir el test que falla**

Crear `api/app/tests/test_reportes_export.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal

from app.services.reportes_export import (
    generar_pdf_financiero,
    generar_pdf_inventario,
    generar_xlsx_financiero,
    generar_xlsx_inventario,
)

_DATOS_FINANCIERO = {
    "desde": datetime(2026, 6, 1, tzinfo=timezone.utc),
    "hasta": datetime(2026, 6, 30, tzinfo=timezone.utc),
    "total_ventas": Decimal("1000.00"),
    "total_gastos": Decimal("400.00"),
    "ganancia_neta": Decimal("600.00"),
    "margen_pct": Decimal("60.00"),
    "margen_pct_anterior": Decimal("50.00"),
    "variacion_ventas_pct": Decimal("10.00"),
    "variacion_ganancia_pct": Decimal("20.00"),
    "ranking_margen": [
        {
            "producto_id": 1,
            "nombre": "Latte",
            "ingresos": Decimal("550.00"),
            "costo_total": Decimal("40.00"),
            "margen": Decimal("510.00"),
            "margen_pct": Decimal("92.73"),
        }
    ],
}

_DATOS_INVENTARIO = {
    "riesgo": [
        {
            "id": 1,
            "nombre": "Leche entera",
            "unidad": "ml",
            "stock_actual": Decimal("500"),
            "stock_minimo": Decimal("1000"),
            "falta": Decimal("500"),
            "costo_reposicion": Decimal("10.00"),
            "productos_afectados": ["Latte", "Capuchino"],
        }
    ]
}


def test_generar_pdf_financiero_produce_pdf_valido():
    buffer = generar_pdf_financiero(_DATOS_FINANCIERO)
    contenido = buffer.read()
    assert contenido[:4] == b"%PDF"


def test_generar_pdf_inventario_produce_pdf_valido():
    buffer = generar_pdf_inventario(_DATOS_INVENTARIO)
    contenido = buffer.read()
    assert contenido[:4] == b"%PDF"


def test_generar_pdf_inventario_sin_riesgo_no_falla():
    buffer = generar_pdf_inventario({"riesgo": []})
    contenido = buffer.read()
    assert contenido[:4] == b"%PDF"


def test_generar_xlsx_financiero_produce_zip_valido():
    buffer = generar_xlsx_financiero(_DATOS_FINANCIERO)
    contenido = buffer.read()
    assert contenido[:2] == b"PK"  # firma de archivo ZIP (XLSX es un ZIP)


def test_generar_xlsx_inventario_produce_zip_valido():
    buffer = generar_xlsx_inventario(_DATOS_INVENTARIO)
    contenido = buffer.read()
    assert contenido[:2] == b"PK"
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_reportes_export.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.reportes_export'`

- [ ] **Step 3: Agregar `reportlab` a `api/requirements.txt`**

Agregar esta línea al final de `api/requirements.txt`:

```
reportlab==4.2.5
```

Instalar en el entorno virtual local:

Run: `cd api && ./.venv/Scripts/pip.exe install reportlab==4.2.5`

- [ ] **Step 4: Crear `api/app/services/reportes_export.py`**

```python
import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_HOUSE = colors.HexColor("#1E3932")
_ACCENT = colors.HexColor("#00754A")
_LIGHT = colors.HexColor("#F2F0EB")
_GREY = colors.HexColor("#6B7280")

_ESTILO_TABLA = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), _HOUSE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
)

_RELLENO_ENCABEZADO = PatternFill(start_color="1E3932", end_color="1E3932", fill_type="solid")
_FUENTE_ENCABEZADO = Font(color="FFFFFF", bold=True)


def _documento_base(buffer: io.BytesIO) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )


def _estilos_parrafo():
    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Heading1"], textColor=_ACCENT, fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], textColor=_HOUSE, fontSize=11, spaceBefore=10, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=base["Normal"], textColor=_GREY, fontSize=9, spaceAfter=8)
    ftr = ParagraphStyle("ftr", parent=base["Normal"], textColor=colors.grey, fontSize=8)
    return h1, h2, sub, ftr


def _tabla(filas: list[list[str]]) -> Table:
    tabla = Table(filas, hAlign="LEFT")
    tabla.setStyle(_ESTILO_TABLA)
    return tabla


def generar_pdf_financiero(datos: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = _documento_base(buffer)
    h1, h2, sub, ftr = _estilos_parrafo()

    story = [Paragraph("Coffee Code — Reporte Financiero", h1)]
    story.append(
        Paragraph(f"Periodo: {datos['desde'].strftime('%d/%m/%Y')} — {datos['hasta'].strftime('%d/%m/%Y')}", sub)
    )
    story.append(
        _tabla(
            [
                ["Ventas", "Gastos", "Ganancia neta", "Margen %"],
                [
                    f"${datos['total_ventas']:,.2f}",
                    f"${datos['total_gastos']:,.2f}",
                    f"${datos['ganancia_neta']:,.2f}",
                    f"{datos['margen_pct']}%",
                ],
            ]
        )
    )

    if datos["ranking_margen"]:
        story.append(Paragraph("Rendimiento de producto", h2))
        story.append(
            _tabla(
                [["Producto", "Ingresos", "Costo estimado", "Margen", "Margen %"]]
                + [
                    [
                        fila["nombre"],
                        f"${fila['ingresos']:,.2f}",
                        f"${fila['costo_total']:,.2f}",
                        f"${fila['margen']:,.2f}",
                        f"{fila['margen_pct']}%",
                    ]
                    for fila in datos["ranking_margen"]
                ]
            )
        )

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(f"Generado por Coffee Code API · {datetime.now().strftime('%d/%m/%Y %H:%M')}", ftr))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_pdf_inventario(datos: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = _documento_base(buffer)
    h1, h2, sub, ftr = _estilos_parrafo()

    story = [Paragraph("Coffee Code — Reporte de Inventario", h1)]
    story.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub))

    if datos["riesgo"]:
        story.append(Paragraph("Riesgo de inventario", h2))
        story.append(
            _tabla(
                [["Ingrediente", "Falta", "Costo de reposición", "Productos afectados"]]
                + [
                    [
                        fila["nombre"],
                        f"{fila['falta']} {fila['unidad']}",
                        f"${fila['costo_reposicion']:,.2f}",
                        ", ".join(fila["productos_afectados"]),
                    ]
                    for fila in datos["riesgo"]
                ]
            )
        )
    else:
        story.append(Paragraph("Sin ingredientes bajo el stock mínimo.", sub))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(f"Generado por Coffee Code API · {datetime.now().strftime('%d/%m/%Y %H:%M')}", ftr))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_xlsx_financiero(datos: dict) -> io.BytesIO:
    libro = Workbook()
    hoja_resumen = libro.active
    hoja_resumen.title = "Resumen financiero"
    hoja_resumen.append(["Métrica", "Valor"])
    for celda in hoja_resumen[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    hoja_resumen.append(["Ventas", float(datos["total_ventas"])])
    hoja_resumen.append(["Gastos", float(datos["total_gastos"])])
    hoja_resumen.append(["Ganancia neta", float(datos["ganancia_neta"])])
    hoja_resumen.append(["Margen %", float(datos["margen_pct"])])

    hoja_ranking = libro.create_sheet("Rendimiento de producto")
    hoja_ranking.append(["Producto", "Ingresos", "Costo estimado", "Margen", "Margen %"])
    for celda in hoja_ranking[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ranking_margen"]:
        hoja_ranking.append(
            [
                fila["nombre"],
                float(fila["ingresos"]),
                float(fila["costo_total"]),
                float(fila["margen"]),
                float(fila["margen_pct"]),
            ]
        )

    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer


def generar_xlsx_inventario(datos: dict) -> io.BytesIO:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Riesgo de inventario"
    hoja.append(["Ingrediente", "Falta", "Unidad", "Costo de reposición", "Productos afectados"])
    for celda in hoja[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["riesgo"]:
        hoja.append(
            [
                fila["nombre"],
                float(fila["falta"]),
                fila["unidad"],
                float(fila["costo_reposicion"]),
                ", ".join(fila["productos_afectados"]),
            ]
        )

    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_reportes_export.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add api/app/services/reportes_export.py api/app/tests/test_reportes_export.py api/requirements.txt
git commit -m "feat(api): generar PDF con reportlab y XLSX con openpyxl para reportes"
```

---

### Task 3: Router `/api/reportes/*` con JSON + descarga, registrado en la API

**Files:**
- Create: `api/app/routers/reportes.py`
- Modify: `api/app/main.py`
- Test: `api/app/tests/test_router_reportes.py` (crear)

**Interfaces:**
- Consumes: `construir_reporte_financiero`, `construir_reporte_inventario` (Task 1); `generar_pdf_financiero`, `generar_pdf_inventario`, `generar_xlsx_financiero`, `generar_xlsx_inventario` (Task 2); `require_rol` (`api/app/security/auth.py`); `RolNombre` (`api/app/core/constants.py`).
- Produces (usado por Task 4, web-admin): endpoints `GET /api/reportes/financiero`, `GET /api/reportes/inventario`, `GET /api/reportes/financiero/pdf`, `GET /api/reportes/financiero/xlsx`, `GET /api/reportes/inventario/pdf`, `GET /api/reportes/inventario/xlsx`.

- [ ] **Step 1: Escribir el test que falla**

Crear `api/app/tests/test_router_reportes.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.constants import EstatusCocinaNombre, EstatusPedidoNombre, RolNombre
from app.data.categorias import Categoria
from app.data.detalle_pedidos import DetallePedido
from app.data.ingredientes import Ingrediente
from app.data.pedidos import Pedido
from app.data.productos import Producto
from app.data.recetas import Receta
from app.data.tickets import Ticket
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


@pytest.fixture()
def categoria(db_session):
    cat = Categoria(nombre="Bebidas calientes", activo=True)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def producto_con_receta(db_session, categoria):
    producto = Producto(
        nombre="Latte", precio_venta=Decimal("55.00"), disponible=True, activo=True, id_categoria=categoria.id
    )
    ingrediente = Ingrediente(
        nombre="Leche entera",
        unidad="ml",
        stock_actual=Decimal("500"),
        stock_minimo=Decimal("1000"),
        costo_unitario=Decimal("0.02"),
        activo=True,
    )
    db_session.add_all([producto, ingrediente])
    db_session.flush()
    receta = Receta(id_producto=producto.id, id_ingrediente=ingrediente.id, cantidad_requerida=Decimal("200"))
    db_session.add(receta)
    db_session.flush()
    return producto, ingrediente


@pytest.fixture()
def venta_de_junio(db_session, catalogos, mesa_libre, usuario_mesero, producto_con_receta):
    producto, _ = producto_con_receta
    fecha = datetime(2026, 6, 15, tzinfo=timezone.utc)
    pedido = Pedido(
        fecha=fecha,
        id_mesa=mesa_libre.id,
        id_usuario=usuario_mesero.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.ENTREGADO].id,
    )
    db_session.add(pedido)
    db_session.flush()
    detalle = DetallePedido(
        cantidad=10,
        precio_unitario=Decimal("55.00"),
        id_producto=producto.id,
        id_pedido=pedido.id,
        id_estatus=catalogos["estatus_cocina"][EstatusCocinaNombre.LISTO].id,
    )
    db_session.add(detalle)
    db_session.flush()
    ticket = Ticket(
        subtotal=Decimal("550.00"),
        iva=Decimal("88.00"),
        total=Decimal("638.00"),
        fecha_emision=fecha,
        id_pedido=pedido.id,
        id_usuario=usuario_mesero.id,
    )
    db_session.add(ticket)
    db_session.flush()
    return ticket


def test_financiero_json_devuelve_ranking_y_margen(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get(
        "/api/reportes/financiero?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total_ventas"] == "638.00"  # Ticket.total incluye IVA (550.00 subtotal * 1.16)
    assert len(cuerpo["ranking_margen"]) == 1
    assert cuerpo["ranking_margen"][0]["nombre"] == "Latte"


def test_financiero_json_rechaza_rol_no_administrador(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.MESERO)

    respuesta = client.get(
        "/api/reportes/financiero",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


def test_inventario_json_devuelve_riesgo(client, catalogos, producto_con_receta):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/inventario", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["riesgo"]) == 1
    assert cuerpo["riesgo"][0]["nombre"] == "Leche entera"
    assert cuerpo["riesgo"][0]["productos_afectados"] == ["Latte"]


def test_financiero_pdf_devuelve_pdf_valido(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get(
        "/api/reportes/financiero/pdf?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.content[:4] == b"%PDF"


def test_financiero_xlsx_devuelve_xlsx_valido(client, catalogos, venta_de_junio):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get(
        "/api/reportes/financiero/xlsx?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert (
        respuesta.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert respuesta.content[:2] == b"PK"


def test_inventario_pdf_devuelve_pdf_valido(client, catalogos, producto_con_receta):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/inventario/pdf", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.content[:4] == b"%PDF"


def test_inventario_xlsx_devuelve_xlsx_valido(client, catalogos, producto_con_receta):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get("/api/reportes/inventario/xlsx", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.content[:2] == b"PK"
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_reportes.py -v`
Expected: FAIL con `404 Not Found` en todas las rutas (el router aún no existe/no está registrado).

- [ ] **Step 3: Crear `api/app/routers/reportes.py`**

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
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> dict:
    desde, hasta = _rango_por_defecto(desde, hasta)
    return construir_reporte_financiero(db, desde, hasta)


@router.get("/inventario", response_model=ReporteInventarioOut)
def inventario(db: Session = Depends(get_db), _=Depends(_solo_admin)) -> dict:
    return construir_reporte_inventario(db)


@router.get("/financiero/pdf")
def financiero_pdf(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_financiero(db, desde, hasta)
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
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_financiero(db, desde, hasta)
    buffer = generar_xlsx_financiero(datos)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_financiero.xlsx"},
    )


@router.get("/inventario/pdf")
def inventario_pdf(db: Session = Depends(get_db), _=Depends(_solo_admin)) -> StreamingResponse:
    datos = construir_reporte_inventario(db)
    buffer = generar_pdf_inventario(datos)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_inventario.pdf"},
    )


@router.get("/inventario/xlsx")
def inventario_xlsx(db: Session = Depends(get_db), _=Depends(_solo_admin)) -> StreamingResponse:
    datos = construir_reporte_inventario(db)
    buffer = generar_xlsx_inventario(datos)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_inventario.xlsx"},
    )
```

- [ ] **Step 4: Registrar el router en `api/app/main.py`**

En `api/app/main.py`, agregar el import junto a los demás routers (después de `from app.routers.recetas import router as recetas_router`):

```python
from app.routers.reportes import router as reportes_router
```

Y agregar `app.include_router(reportes_router)` después de `app.include_router(admin_router)`:

```python
app.include_router(admin_router)
app.include_router(reportes_router)
app.include_router(websockets_router)
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_reportes.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Ejecutar toda la suite de la API para confirmar que no hay regresiones**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/ -v`
Expected: PASS (todos los tests existentes + los nuevos)

- [ ] **Step 7: Commit**

```bash
git add api/app/routers/reportes.py api/app/main.py api/app/tests/test_router_reportes.py
git commit -m "feat(api): exponer /api/reportes/financiero e /inventario con JSON y descarga PDF/XLSX"
```

---

### Task 4: `api_client.py` de web-admin — nuevas funciones de consumo

**Files:**
- Modify: `web-admin/app/api_client.py`
- Test: `web-admin/tests/test_api_client.py`

**Interfaces:**
- Consumes: `_request(method, base_url, path, token=None, **kwargs)` (ya existe en el mismo archivo), `ApiError` (ya existe).
- Produces (usado por Task 5 y 6): `obtener_reporte_financiero(base_url, token, desde, hasta) -> dict`, `obtener_reporte_inventario(base_url, token) -> dict`, `descargar_reporte(base_url, token, categoria, formato, params=None) -> requests.Response`.

- [ ] **Step 1: Leer el test existente para conocer el patrón de mocking**

Ver `web-admin/tests/test_api_client.py` (usa la librería `responses` para mockear `requests`). Confirmar que usa `BASE_URL = "http://testserver"` y `responses.add(responses.GET, ...)`.

Run: `cd web-admin && ./.venv/Scripts/python.exe -m pytest tests/test_api_client.py -v`
Expected: PASS (tests existentes, para tener una baseline antes de agregar los nuevos)

- [ ] **Step 2: Escribir los tests que fallan**

Agregar al final de `web-admin/tests/test_api_client.py`:

```python
def test_obtener_reporte_financiero(mock_api):
    mock_api.get(
        f"{BASE_URL}/api/reportes/financiero",
        json={"total_ventas": "550.00", "ranking_margen": []},
        status=200,
    )
    resultado = obtener_reporte_financiero(BASE_URL, "token", "2026-06-01", "2026-06-30")
    assert resultado["total_ventas"] == "550.00"


def test_obtener_reporte_inventario(mock_api):
    mock_api.get(f"{BASE_URL}/api/reportes/inventario", json={"riesgo": []}, status=200)
    resultado = obtener_reporte_inventario(BASE_URL, "token")
    assert resultado == {"riesgo": []}


def test_descargar_reporte_devuelve_response_crudo(mock_api):
    mock_api.get(
        f"{BASE_URL}/api/reportes/financiero/pdf",
        body=b"%PDF-contenido-simulado",
        status=200,
        content_type="application/pdf",
    )
    respuesta = descargar_reporte(BASE_URL, "token", "financiero", "pdf", {"desde": "2026-06-01"})
    assert respuesta.status_code == 200
    assert respuesta.content == b"%PDF-contenido-simulado"


def test_descargar_reporte_lanza_apierror_en_4xx(mock_api):
    mock_api.get(
        f"{BASE_URL}/api/reportes/inventario/xlsx",
        json={"detail": "No autorizado"},
        status=403,
    )
    with pytest.raises(ApiError) as exc_info:
        descargar_reporte(BASE_URL, "token", "inventario", "xlsx")
    assert exc_info.value.status_code == 403
```

Revisar el inicio de `web-admin/tests/test_api_client.py` para confirmar los imports/fixtures ya usados (`mock_api`, `BASE_URL`, `pytest`) y agregar a la línea de imports desde `app.api_client`:

```python
from app.api_client import (
    ApiError,
    ...  # (mantener los imports existentes)
    descargar_reporte,
    obtener_reporte_financiero,
    obtener_reporte_inventario,
)
```

- [ ] **Step 3: Ejecutar el test y confirmar que falla**

Run: `cd web-admin && ./.venv/Scripts/python.exe -m pytest tests/test_api_client.py -v`
Expected: FAIL con `ImportError: cannot import name 'obtener_reporte_financiero'`

- [ ] **Step 4: Editar `web-admin/app/api_client.py`**

Reemplazar la función `obtener_reporte_admin` (última función del archivo) por:

```python
def obtener_reporte_admin(base_url: str, token: str, desde: str, hasta: str) -> dict:
    return _request(
        "GET", base_url, "/api/reportes", token=token, params={"desde": desde, "hasta": hasta}
    )


def obtener_reporte_financiero(base_url: str, token: str, desde: str, hasta: str) -> dict:
    return _request(
        "GET", base_url, "/api/reportes/financiero", token=token, params={"desde": desde, "hasta": hasta}
    )


def obtener_reporte_inventario(base_url: str, token: str) -> dict:
    return _request("GET", base_url, "/api/reportes/inventario", token=token)


def descargar_reporte(
    base_url: str, token: str, categoria: str, formato: str, params: dict | None = None
) -> requests.Response:
    try:
        respuesta = requests.request(
            "GET",
            f"{base_url}/api/reportes/{categoria}/{formato}",
            headers=_headers(token),
            params=params or {},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ApiError(None, f"No se pudo conectar con la API: {exc}") from exc

    if respuesta.status_code >= 400:
        try:
            detalle = respuesta.json().get("detail", respuesta.text)
        except ValueError:
            detalle = respuesta.text
        raise ApiError(respuesta.status_code, detalle)

    return respuesta
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd web-admin && ./.venv/Scripts/python.exe -m pytest tests/test_api_client.py -v`
Expected: PASS (todos los tests, incluidos los 4 nuevos)

- [ ] **Step 6: Commit**

```bash
git add web-admin/app/api_client.py web-admin/tests/test_api_client.py
git commit -m "feat(web-admin): agregar funciones de api_client para reportes financiero/inventario"
```

---

### Task 5: Dashboard con 2 pestañas (Financiero / Inventario), sin lógica de negocio

**Files:**
- Modify: `web-admin/app/blueprints/dashboard.py`
- Modify: `web-admin/app/templates/dashboard.html`
- Modify: `web-admin/app/static/js/charts-theme.js` (sin cambios de contenido, solo confirmar que sigue siendo consumido)
- Test: `web-admin/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `obtener_reporte_financiero`, `obtener_reporte_inventario` (Task 4).
- Produces: nada consumido por tasks posteriores (vista final).

- [ ] **Step 1: Escribir el test que falla**

Reemplazar el contenido completo de `web-admin/tests/test_dashboard.py`:

```python
import pytest
import responses
from flask import Blueprint

from app.blueprints.dashboard import bp as dashboard_bp

BASE_URL = "http://testserver"


def _stub_reportes_bp() -> Blueprint:
    bp = Blueprint("reportes", __name__, url_prefix="/reportes")

    @bp.route("/financiero/exportar.<formato>")
    def exportar_financiero(formato):
        return ""

    @bp.route("/inventario/exportar.<formato>")
    def exportar_inventario(formato):
        return ""

    return bp


@pytest.fixture()
def client(app):
    if "dashboard" not in app.blueprints:
        app.register_blueprint(dashboard_bp)
    if "reportes" not in app.blueprints:
        try:
            from app.blueprints.reportes import bp as reportes_bp
        except Exception:
            reportes_bp = _stub_reportes_bp()
        app.register_blueprint(reportes_bp)
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_dashboard_muestra_bloque_financiero_e_inventario(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero",
        json={
            "desde": "2026-06-01T00:00:00",
            "hasta": "2026-06-30T00:00:00",
            "total_ventas": "1000.00",
            "total_gastos": "400.00",
            "ganancia_neta": "600.00",
            "margen_pct": "60.00",
            "margen_pct_anterior": "50.00",
            "variacion_ventas_pct": "10.00",
            "variacion_ganancia_pct": "20.00",
            "ranking_margen": [
                {
                    "producto_id": 1,
                    "nombre": "Latte",
                    "ingresos": "550.00",
                    "costo_total": "40.00",
                    "margen": "510.00",
                    "margen_pct": "92.73",
                }
            ],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario",
        json={
            "riesgo": [
                {
                    "id": 1,
                    "nombre": "Leche entera",
                    "unidad": "ml",
                    "stock_actual": "500",
                    "stock_minimo": "1000",
                    "falta": "500",
                    "costo_reposicion": "10.00",
                    "productos_afectados": ["Latte"],
                }
            ]
        },
        status=200,
    )

    respuesta = client.get("/?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "Ganancia neta" in cuerpo
    assert "Leche entera" in cuerpo
    assert "Latte" in cuerpo


def test_dashboard_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd web-admin && ./.venv/Scripts/python.exe -m pytest tests/test_dashboard.py -v`
Expected: FAIL — el mock del endpoint viejo (`/api/reportes`, `/productos`, etc.) ya no aplica y `dashboard.py` sigue llamando a las funciones viejas, así que `responses` lanzará `ConnectionError` por una llamada no mockeada.

- [ ] **Step 3: Reemplazar `web-admin/app/blueprints/dashboard.py`**

```python
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request

from app.api_client import obtener_reporte_financiero, obtener_reporte_inventario
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("dashboard", __name__)


def _parsear_fecha(valor: str | None, default: date) -> date:
    if not valor:
        return default
    return datetime.strptime(valor, "%Y-%m-%d").date()


@bp.route("/")
@login_required
def index():
    token = current_token()
    base_url = api_base_url()

    hoy = date.today()
    hasta = _parsear_fecha(request.args.get("hasta"), hoy)
    desde = _parsear_fecha(request.args.get("desde"), hoy - timedelta(days=30))

    financiero = obtener_reporte_financiero(base_url, token, desde.isoformat(), hasta.isoformat())
    inventario = obtener_reporte_inventario(base_url, token)

    return render_template(
        "dashboard.html",
        desde=desde,
        hasta=hasta,
        financiero=financiero,
        inventario=inventario,
    )
```

- [ ] **Step 4: Reemplazar `web-admin/app/templates/dashboard.html`**

```html
{% extends "base.html" %}
{% block title %}Dashboard — Coffee Code Admin{% endblock %}
{% block content %}
<div x-data="{ tab: 'financiero' }">
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-semibold text-starbucks">Dashboard</h1>
    <div class="flex gap-2">
      <button @click="tab = 'financiero'" class="btn" :class="tab === 'financiero' ? 'btn-primary' : 'btn-ghost'">Financiero</button>
      <button @click="tab = 'inventario'" class="btn" :class="tab === 'inventario' ? 'btn-primary' : 'btn-ghost'">Inventario</button>
    </div>
  </div>

  <div x-show="tab === 'financiero'">
    <form method="get" class="flex items-center gap-2 text-sm mb-6">
      <input type="date" name="desde" value="{{ desde.isoformat() }}" class="input-field !w-auto py-1.5">
      <span class="text-black/58">a</span>
      <input type="date" name="hasta" value="{{ hasta.isoformat() }}" class="input-field !w-auto py-1.5">
      <button type="submit" class="btn btn-primary">Filtrar</button>
      <a href="{{ url_for('reportes.exportar_financiero', formato='pdf', desde=desde.isoformat(), hasta=hasta.isoformat()) }}" class="btn btn-outline">PDF</a>
      <a href="{{ url_for('reportes.exportar_financiero', formato='xlsx', desde=desde.isoformat(), hasta=hasta.isoformat()) }}" class="btn btn-outline">XLSX</a>
    </form>

    <div class="grid grid-cols-4 gap-4 mb-8">
      <div class="card p-5">
        <div class="text-xs uppercase tracking-wide text-black/58">Ventas</div>
        <div class="text-2xl font-semibold mt-1">${{ "%.2f"|format(financiero.total_ventas|float) }}</div>
        {% if financiero.variacion_ventas_pct is not none %}
        <div class="text-xs mt-1 {{ 'text-starbucks' if financiero.variacion_ventas_pct|float >= 0 else 'text-[#c82014]' }}">
          {{ "+" if financiero.variacion_ventas_pct|float >= 0 else "" }}{{ financiero.variacion_ventas_pct }}% vs. periodo anterior
        </div>
        {% endif %}
      </div>
      <div class="card p-5">
        <div class="text-xs uppercase tracking-wide text-black/58">Gastos</div>
        <div class="text-2xl font-semibold mt-1">${{ "%.2f"|format(financiero.total_gastos|float) }}</div>
      </div>
      <div class="card p-5">
        <div class="text-xs uppercase tracking-wide text-black/58">Ganancia neta</div>
        <div class="text-2xl font-semibold mt-1">${{ "%.2f"|format(financiero.ganancia_neta|float) }}</div>
        {% if financiero.variacion_ganancia_pct is not none %}
        <div class="text-xs mt-1 {{ 'text-starbucks' if financiero.variacion_ganancia_pct|float >= 0 else 'text-[#c82014]' }}">
          {{ "+" if financiero.variacion_ganancia_pct|float >= 0 else "" }}{{ financiero.variacion_ganancia_pct }}% vs. periodo anterior
        </div>
        {% endif %}
      </div>
      <div class="card p-5">
        <div class="text-xs uppercase tracking-wide text-black/58">Margen</div>
        <div class="text-2xl font-semibold mt-1">{{ financiero.margen_pct }}%</div>
        <div class="text-xs mt-1 text-black/58">Periodo anterior: {{ financiero.margen_pct_anterior }}%</div>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-6 mb-8">
      <div class="card p-5">
        <h2 class="text-lg font-semibold mb-3">Ventas vs. gastos</h2>
        <canvas id="chartVentasGastos" height="180"></canvas>
      </div>
      <div class="card p-5">
        <h2 class="text-lg font-semibold mb-3">Ranking de margen por producto</h2>
        <canvas id="chartMargen" height="180"></canvas>
      </div>
    </div>

    <div class="card overflow-hidden">
      <div class="p-5 pb-0">
        <h2 class="text-lg font-semibold mb-3">Rendimiento de producto</h2>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Ingresos</th>
            <th>Costo estimado</th>
            <th>Margen</th>
            <th>Margen %</th>
          </tr>
        </thead>
        <tbody>
          {% for fila in financiero.ranking_margen %}
          <tr>
            <td>{{ fila.nombre }}</td>
            <td>${{ "%.2f"|format(fila.ingresos|float) }}</td>
            <td>${{ "%.2f"|format(fila.costo_total|float) }}</td>
            <td>${{ "%.2f"|format(fila.margen|float) }}</td>
            <td>{{ fila.margen_pct }}%</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <div x-show="tab === 'inventario'">
    <div class="flex justify-end gap-2 mb-6">
      <a href="{{ url_for('reportes.exportar_inventario', formato='pdf') }}" class="btn btn-outline">PDF</a>
      <a href="{{ url_for('reportes.exportar_inventario', formato='xlsx') }}" class="btn btn-outline">XLSX</a>
    </div>
    <div class="card overflow-hidden">
      <div class="p-5 pb-0">
        <h2 class="text-lg font-semibold mb-3">Riesgo de inventario</h2>
      </div>
      {% if inventario.riesgo %}
      <table class="data-table">
        <thead>
          <tr>
            <th>Ingrediente</th>
            <th>Falta</th>
            <th>Costo de reposición</th>
            <th>Productos afectados</th>
          </tr>
        </thead>
        <tbody>
          {% for fila in inventario.riesgo %}
          <tr class="row-risk">
            <td>{{ fila.nombre }}</td>
            <td>{{ fila.falta }} {{ fila.unidad }}</td>
            <td>${{ "%.2f"|format(fila.costo_reposicion|float) }}</td>
            <td>{{ fila.productos_afectados | join(", ") }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
      <p class="text-starbucks text-sm p-5">Sin ingredientes bajo el stock mínimo.</p>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/charts-theme.js') }}"></script>
<script>
  new Chart(document.getElementById('chartVentasGastos'), {
    type: 'bar',
    data: {
      labels: ['Ventas', 'Gastos', 'Ganancia neta'],
      datasets: [{
        label: 'Periodo actual',
        data: [{{ financiero.total_ventas }}, {{ financiero.total_gastos }}, {{ financiero.ganancia_neta }}],
        backgroundColor: [coffeeChartPalette.accent, coffeeChartPalette.negative, coffeeChartPalette.positive],
        borderRadius: 6,
      }]
    },
    options: { plugins: { legend: { display: false } } }
  });

  new Chart(document.getElementById('chartMargen'), {
    type: 'bar',
    data: {
      labels: [{% for fila in financiero.ranking_margen %}{{ fila.nombre|tojson }},{% endfor %}],
      datasets: [{
        label: 'Margen %',
        data: [{% for fila in financiero.ranking_margen %}{{ fila.margen_pct }},{% endfor %}],
        backgroundColor: coffeeChartPalette.uplift,
        borderRadius: 6,
      }]
    },
    options: { indexAxis: 'y', plugins: { legend: { display: false } } }
  });
</script>
{% endblock %}
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd web-admin && ./.venv/Scripts/python.exe -m pytest tests/test_dashboard.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add web-admin/app/blueprints/dashboard.py web-admin/app/templates/dashboard.html web-admin/tests/test_dashboard.py
git commit -m "feat(web-admin): dashboard con pestanas Financiero/Inventario consumiendo la API"
```

---

### Task 6: Blueprint de reportes reducido a proxy de descarga; eliminar generación de archivos en Flask

**Files:**
- Modify: `web-admin/app/blueprints/reportes.py`
- Delete: `web-admin/app/reportes.py`
- Delete: `web-admin/app/templates/reportes/reporte_pdf.html`
- Delete: `web-admin/tests/test_reportes.py` (tests del módulo eliminado)
- Delete: `web-admin/tests/test_reportes_export.py` (tests del WeasyPrint eliminado)
- Create: `web-admin/tests/test_reportes_proxy.py`

**Interfaces:**
- Consumes: `descargar_reporte` (Task 4), `current_token`/`api_base_url`/`login_required` (`web-admin/app/auth.py`, ya existen).
- Produces: rutas Flask `reportes.exportar_financiero`, `reportes.exportar_inventario` (usadas por los `url_for(...)` de Task 5's `dashboard.html`).

- [ ] **Step 1: Escribir el test que falla**

Crear `web-admin/tests/test_reportes_proxy.py`:

```python
import pytest
import responses

from app.blueprints.reportes import bp as reportes_bp

BASE_URL = "http://testserver"


@pytest.fixture()
def client(app):
    if "reportes" not in app.blueprints:
        app.register_blueprint(reportes_bp)
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_exportar_financiero_pdf_retransmite_bytes(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero/pdf",
        body=b"%PDF-contenido",
        status=200,
        content_type="application/pdf",
    )

    respuesta = client.get("/reportes/financiero/exportar.pdf?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    assert respuesta.content_type == "application/pdf"
    assert respuesta.data == b"%PDF-contenido"


@responses.activate
def test_exportar_inventario_xlsx_retransmite_bytes(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario/xlsx",
        body=b"PK-contenido-zip",
        status=200,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    respuesta = client.get("/reportes/inventario/exportar.xlsx")

    assert respuesta.status_code == 200
    assert respuesta.data == b"PK-contenido-zip"


def test_exportar_formato_invalido_da_404(client):
    _login_como_admin(client)
    respuesta = client.get("/reportes/financiero/exportar.docx")
    assert respuesta.status_code == 404


@responses.activate
def test_exportar_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/reportes/financiero/exportar.pdf", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd web-admin && ./.venv/Scripts/python.exe -m pytest tests/test_reportes_proxy.py -v`
Expected: FAIL (rutas `/reportes/financiero/exportar.pdf` e `/reportes/inventario/exportar.xlsx` no existen todavía — 404 en las que esperan 200).

- [ ] **Step 3: Reemplazar `web-admin/app/blueprints/reportes.py`**

```python
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, abort, request

from app.api_client import descargar_reporte
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("reportes", __name__, url_prefix="/reportes")

_FORMATOS_VALIDOS = {"pdf", "xlsx"}


def _parsear_fecha(valor: str | None, default: date) -> date:
    if not valor:
        return default
    return datetime.strptime(valor, "%Y-%m-%d").date()


def _proxy(categoria: str, formato: str, params: dict) -> Response:
    if formato not in _FORMATOS_VALIDOS:
        abort(404)

    token = current_token()
    base_url = api_base_url()
    respuesta = descargar_reporte(base_url, token, categoria, formato, params)

    return Response(
        respuesta.content,
        mimetype=respuesta.headers.get("Content-Type", "application/octet-stream"),
        headers={
            "Content-Disposition": respuesta.headers.get(
                "Content-Disposition", f"attachment; filename=reporte_{categoria}.{formato}"
            )
        },
    )


@bp.route("/financiero/exportar.<formato>")
@login_required
def exportar_financiero(formato: str):
    hoy = date.today()
    hasta = _parsear_fecha(request.args.get("hasta"), hoy)
    desde = _parsear_fecha(request.args.get("desde"), hoy - timedelta(days=30))
    return _proxy("financiero", formato, {"desde": desde.isoformat(), "hasta": hasta.isoformat()})


@bp.route("/inventario/exportar.<formato>")
@login_required
def exportar_inventario(formato: str):
    return _proxy("inventario", formato, {})
```

- [ ] **Step 4: Eliminar archivos que ya no aplican**

```bash
rm web-admin/app/reportes.py
rm web-admin/app/templates/reportes/reporte_pdf.html
rmdir web-admin/app/templates/reportes 2>/dev/null || true
rm web-admin/tests/test_reportes.py
rm web-admin/tests/test_reportes_export.py
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd web-admin && ./.venv/Scripts/python.exe -m pytest tests/test_reportes_proxy.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Ejecutar toda la suite de web-admin para confirmar que no hay regresiones**

Run: `cd web-admin && ./.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS (todos los tests; ya no debería existir el test de WeasyPrint que fallaba localmente por falta de GTK)

- [ ] **Step 7: Commit**

```bash
git add web-admin/app/blueprints/reportes.py web-admin/tests/test_reportes_proxy.py
git rm web-admin/app/reportes.py web-admin/app/templates/reportes/reporte_pdf.html web-admin/tests/test_reportes.py web-admin/tests/test_reportes_export.py
git commit -m "refactor(web-admin): reportes.py como proxy puro de descarga, sin generar archivos"
```

---

### Task 7: Quitar WeasyPrint del proyecto (dependencia y Dockerfile)

**Files:**
- Modify: `web-admin/requirements.txt`
- Modify: `web-admin/Dockerfile`

**Interfaces:**
- Consumes: nada (limpieza de dependencias ya no usadas tras la Task 6).
- Produces: nada consumido por otras tasks; verificado en Task 8 (Docker build).

- [ ] **Step 1: Editar `web-admin/requirements.txt`**

Quitar la línea `WeasyPrint==63.1`. Contenido final:

```
Flask==3.1.0
requests==2.32.3
python-dotenv==1.0.1
openpyxl==3.1.5
pytest==8.3.4
responses==0.25.3
```

- [ ] **Step 2: Editar `web-admin/Dockerfile`**

Reemplazar el contenido completo (ya no se necesitan las librerías nativas de GTK/Pango/gdk-pixbuf que exigía WeasyPrint):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "wsgi.py"]
```

- [ ] **Step 3: Confirmar que no queda ninguna referencia a WeasyPrint en el repo**

Run: `grep -rn "weasyprint\|WeasyPrint" web-admin/ --include="*.py" --include="*.txt" --include="Dockerfile"`
Expected: sin resultados (exit code distinto de 0 / salida vacía)

- [ ] **Step 4: Commit**

```bash
git add web-admin/requirements.txt web-admin/Dockerfile
git commit -m "chore(web-admin): quitar WeasyPrint y sus dependencias nativas de GTK"
```

---

### Task 8: Colección de Postman + verificación end-to-end contra Docker

**Files:**
- Modify: `postman/coffee-code.postman_collection.json`

**Interfaces:**
- Consumes: los 6 endpoints creados en Task 3.
- Produces: nada (última tarea del plan).

- [ ] **Step 1: Abrir `postman/coffee-code.postman_collection.json` y localizar la carpeta de Admin/Reportes**

Ubicar la carpeta donde ya vive el request de `GET /api/reportes` (agregado en una sesión anterior) para seguir el mismo estilo de request (headers `Authorization: Bearer {{token_admin}}`, mismo `baseUrl` de variable de colección).

- [ ] **Step 2: Agregar 6 requests nuevos a esa carpeta**

Agregar, siguiendo exactamente el formato de un request existente en la colección (mismo esquema de `header`, `url` con `{{baseUrl}}`, `auth` o header manual de Bearer):
- `GET {{baseUrl}}/api/reportes/financiero?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59`
- `GET {{baseUrl}}/api/reportes/inventario`
- `GET {{baseUrl}}/api/reportes/financiero/pdf?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59`
- `GET {{baseUrl}}/api/reportes/financiero/xlsx?desde=2026-06-01T00:00:00&hasta=2026-06-30T23:59:59`
- `GET {{baseUrl}}/api/reportes/inventario/pdf`
- `GET {{baseUrl}}/api/reportes/inventario/xlsx`

- [ ] **Step 3: Validar que el JSON de la colección sigue siendo válido**

Run: `python -c "import json; json.load(open('postman/coffee-code.postman_collection.json', encoding='utf-8'))"`
Expected: sin salida (si el JSON es inválido, lanzará `json.decoder.JSONDecodeError`)

- [ ] **Step 4: Commit**

```bash
git add postman/coffee-code.postman_collection.json
git commit -m "docs(postman): agregar requests de /api/reportes/financiero e /inventario"
```

- [ ] **Step 5: Rebuild y verificación manual end-to-end contra Docker**

```bash
docker compose up -d --build
```

Esperar a que `coffee_code_api` y `coffee_code_web` terminen de construir (la imagen de `web-admin` ahora es más ligera al no instalar GTK). Luego:

```bash
curl -s http://localhost:8010/health
curl -s http://localhost:8020/health
```

Expected: ambos devuelven `{"status": "ok"}` (o el healthcheck equivalente de FastAPI).

Login y verificación manual del dashboard con datos reales (usar las credenciales de `admin@coffeecode.com` ya sembradas):

```bash
curl -s -c /tmp/cc_cookies.txt -X POST http://localhost:8020/login \
  -d "correo=admin@coffeecode.com&password=Admin123!" -o /dev/null -w "%{http_code}\n"

curl -s -b /tmp/cc_cookies.txt "http://localhost:8020/?desde=2026-05-01&hasta=2026-07-02" \
  | grep -o "Ganancia neta\|Riesgo de inventario" | sort -u

curl -s -b /tmp/cc_cookies.txt \
  "http://localhost:8020/reportes/financiero/exportar.pdf?desde=2026-05-01&hasta=2026-07-02" \
  -o /tmp/reporte_financiero.pdf -w "%{http_code}\n"
file /tmp/reporte_financiero.pdf

curl -s -b /tmp/cc_cookies.txt "http://localhost:8020/reportes/inventario/exportar.xlsx" \
  -o /tmp/reporte_inventario.xlsx -w "%{http_code}\n"
file /tmp/reporte_inventario.xlsx
```

Expected: login `302`, dashboard muestra ambos bloques, PDF (`file` reporta `PDF document`), XLSX (`file` reporta `Microsoft Excel 2007+`).

No hay Step de commit aquí — este paso es solo verificación manual, no produce cambios de código.
