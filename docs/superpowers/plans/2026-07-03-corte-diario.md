# Corte Diario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir generar, desde el panel web-admin, un corte de caja diario (un registro por día natural) que resume ventas/gastos/ganancia neta y el desglose por método de pago de ese día, con historial consultable. Es puramente informativo — no bloquea ni concilia efectivo físico — y es regenerable (upsert) si se vuelve a pedir para la misma fecha.

**Architecture:** Dos tablas nuevas (`CORTES_DIARIOS` + `CORTE_METODOS_PAGO`, ésta como tabla hija porque `METODOS_PAGO` es catálogo abierto) vía migración Alembic. Servicio puro que calcula desde `TICKETS`/`PAGOS`/`GASTOS` filtrando por el día exacto (mismo patrón de agregación SQL que `api/app/services/reportes.py`). Router `/api/cortes-diarios` gated a Administrador. Página nueva en web-admin con botón "Generar" + historial.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + Pydantic (API), Flask + Jinja2 + Alpine.js (web-admin), pytest (ambos lados).

## Global Constraints

- Un corte por **día natural**, no por turno. Regenerar la misma fecha hace upsert, no crea duplicados ni falla.
- Sin conciliación de efectivo físico, sin bloqueo/cierre del día — es un snapshot informativo (decidido explícitamente con el usuario).
- Solo rol Administrador puede generar/consultar (se genera exclusivamente desde web-admin).
- Migraciones versionadas con Alembic — nunca `Base.metadata.create_all` en producción.
- No reiniciar el stack Docker corriendo hasta que todas las piezas de este plan (y de los otros 4 planes paralelos) estén completas — verificar cada paso con pytest, no con recarga en vivo.

---

### Task 1: Esquema — migración Alembic

**Files:**
- Create: `api/app/data/cortes_diarios.py`
- Modify: `api/app/data/__init__.py`
- Create: `api/alembic/versions/<hash>_corte_diario.py` (el hash lo genera Alembic; no inventarlo a mano)

**Interfaces:**
- Produces: modelos SQLAlchemy `CorteDiario` (tabla `cortes_diarios`) y `CorteMetodoPago` (tabla `corte_metodos_pago`), registrados en `Base.metadata` para que Alembic los detecte con autogenerate.

- [ ] **Step 1: Crear el modelo SQLAlchemy**

Crear `api/app/data/cortes_diarios.py`:

```python
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class CorteDiario(Base):
    __tablename__ = "cortes_diarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    total_ventas: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_gastos: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    ganancia_neta: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    num_pedidos: Mapped[int] = mapped_column(Integer, nullable=False)
    num_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    generado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    usuario: Mapped["Usuario"] = relationship()
    desglose_metodos: Mapped[list["CorteMetodoPago"]] = relationship(
        back_populates="corte", cascade="all, delete-orphan"
    )


class CorteMetodoPago(Base):
    __tablename__ = "corte_metodos_pago"

    id_corte: Mapped[int] = mapped_column(ForeignKey("cortes_diarios.id"), primary_key=True)
    id_metodo_pago: Mapped[int] = mapped_column(ForeignKey("metodos_pago.id"), primary_key=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    corte: Mapped["CorteDiario"] = relationship(back_populates="desglose_metodos")
    metodo: Mapped["MetodoPago"] = relationship()
```

- [ ] **Step 2: Registrar los modelos en `app/data/__init__.py`**

Agregar, después de `from app.data.gastos import Gasto`:

```python
from app.data.cortes_diarios import CorteDiario, CorteMetodoPago
```

Y agregar `"CorteDiario"`, `"CorteMetodoPago"` a `__all__`.

- [ ] **Step 3: Generar la migración con Alembic**

Run: `cd api && ./.venv/Scripts/python.exe -m alembic revision --autogenerate -m "corte diario"`
Expected: crea un archivo nuevo en `api/alembic/versions/` con `op.create_table('cortes_diarios', ...)` y `op.create_table('corte_metodos_pago', ...)`.

- [ ] **Step 4: Revisar el archivo generado a mano**

Abrir el archivo generado y confirmar que:
- `cortes_diarios.fecha` tiene `unique=True`.
- `corte_metodos_pago` tiene `sa.PrimaryKeyConstraint('id_corte', 'id_metodo_pago')` (PK compuesta, no un `id` autoincremental separado — si Alembic generó un PK distinto por accidente, corregirlo a mano para que coincida con el modelo del Step 1).
- Ambas tienen sus `ForeignKeyConstraint` correctos (`usuarios.id`, `metodos_pago.id`, `cortes_diarios.id`).

- [ ] **Step 5: Aplicar la migración contra la base de datos de test**

Run: `cd api && ./.venv/Scripts/python.exe -m alembic -x db_url=$TEST_DATABASE_URL upgrade head` — si el proyecto no usa `-x db_url`, usar el mecanismo real ya documentado en `api/README.md` o en el propio `alembic.ini`/`env.py` para apuntar a la DB de test. Alternativamente, dado que los tests de pytest usan `Base.metadata.create_all(eng)` (ver `api/app/tests/conftest.py:52`) y no corren migraciones directamente, basta con confirmar que el modelo nuevo se crea correctamente en ese `create_all` — no es estrictamente necesario aplicar la migración contra la DB de test para que los tests de pytest pasen, pero SÍ es necesario para que la migración funcione contra la DB real de desarrollo/producción más adelante (fuera del alcance verificable sin reiniciar el stack).

- [ ] **Step 6: Verificar que los modelos importan sin errores**

Run: `cd api && ./.venv/Scripts/python.exe -c "from app.data.cortes_diarios import CorteDiario, CorteMetodoPago; print('ok')"`
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add api/app/data/cortes_diarios.py api/app/data/__init__.py api/alembic/versions/
git commit -m "feat(api): agregar tablas cortes_diarios y corte_metodos_pago"
```

---

### Task 2: Servicio de cálculo del corte

**Files:**
- Create: `api/app/services/cortes_diarios.py`
- Test: `api/app/tests/test_cortes_diarios_service.py`

**Interfaces:**
- Consumes: `CorteDiario`, `CorteMetodoPago` (Task 1); `Ticket`, `Pago`, `MetodoPago`, `Gasto`, `Pedido` (ya existen).
- Produces:
  - `generar_o_actualizar_corte(db, fecha: date, id_usuario: int) -> CorteDiario` (calcula y hace upsert)
  - `obtener_corte(db, fecha: date) -> CorteDiario | None`
  - `listar_cortes(db, desde: date, hasta: date) -> list[CorteDiario]`

- [ ] **Step 1: Escribir los tests que deben fallar**

Crear `api/app/tests/test_cortes_diarios_service.py`:

```python
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.core.constants import EstatusPedidoNombre, MetodoPagoNombre, RolNombre
from app.data.detalle_pedidos import DetallePedido
from app.data.gastos import Gasto
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.data.usuarios import Usuario
from app.security.auth import hash_password
from app.services.cortes_diarios import generar_o_actualizar_corte, listar_cortes, obtener_corte


@pytest.fixture()
def admin_user(db_session, catalogos):
    usuario = Usuario(
        nombre="Admin", apellido_paterno="Test", correo_electronico="admin.test@coffeecode.com",
        password_hash=hash_password("Test1234!"), id_rol=catalogos["roles"][RolNombre.ADMINISTRADOR].id,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _crear_venta(db_session, catalogos, mesa_libre, admin_user, fecha, monto, metodo):
    pedido = Pedido(
        id_mesa=mesa_libre.id, id_usuario=admin_user.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.ENTREGADO].id,
        fecha=fecha, total=monto,
    )
    db_session.add(pedido)
    db_session.flush()
    ticket = Ticket(
        subtotal=monto, iva=Decimal("0"), total=monto,
        id_pedido=pedido.id, id_usuario=admin_user.id, fecha_emision=fecha,
    )
    db_session.add(ticket)
    db_session.flush()
    pago = Pago(
        monto_recibido=monto, cambio=Decimal("0"), id_ticket=ticket.id,
        id_metodo=catalogos["metodos_pago"][metodo].id,
    )
    db_session.add(pago)
    db_session.flush()
    return pedido, ticket


def test_generar_corte_calcula_totales_del_dia(db_session, catalogos, mesa_libre, admin_user):
    dia = datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc)
    _crear_venta(db_session, catalogos, mesa_libre, admin_user, dia, Decimal("100.00"), MetodoPagoNombre.EFECTIVO)
    _crear_venta(db_session, catalogos, mesa_libre, admin_user, dia, Decimal("50.00"), MetodoPagoNombre.TARJETA_DEBITO)
    db_session.add(Gasto(monto=Decimal("30.00"), concepto="Insumos", fecha_gasto=dia, id_usuario=admin_user.id))
    db_session.flush()

    corte = generar_o_actualizar_corte(db_session, date(2026, 6, 15), admin_user.id)

    assert corte.total_ventas == Decimal("150.00")
    assert corte.total_gastos == Decimal("30.00")
    assert corte.ganancia_neta == Decimal("120.00")
    assert corte.num_tickets == 2
    montos_por_metodo = {d.metodo.nombre: d.monto for d in corte.desglose_metodos}
    assert montos_por_metodo[MetodoPagoNombre.EFECTIVO] == Decimal("100.00")
    assert montos_por_metodo[MetodoPagoNombre.TARJETA_DEBITO] == Decimal("50.00")


def test_generar_corte_es_upsert_no_duplica(db_session, catalogos, mesa_libre, admin_user):
    dia = datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc)
    _crear_venta(db_session, catalogos, mesa_libre, admin_user, dia, Decimal("100.00"), MetodoPagoNombre.EFECTIVO)
    db_session.flush()

    generar_o_actualizar_corte(db_session, date(2026, 6, 16), admin_user.id)

    _crear_venta(db_session, catalogos, mesa_libre, admin_user, dia, Decimal("40.00"), MetodoPagoNombre.EFECTIVO)
    db_session.flush()
    corte_regenerado = generar_o_actualizar_corte(db_session, date(2026, 6, 16), admin_user.id)

    assert corte_regenerado.total_ventas == Decimal("140.00")
    todos = listar_cortes(db_session, date(2026, 6, 16), date(2026, 6, 16))
    assert len(todos) == 1


def test_obtener_corte_inexistente_devuelve_none(db_session, catalogos):
    assert obtener_corte(db_session, date(2099, 1, 1)) is None
```

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_cortes_diarios_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.cortes_diarios'`

- [ ] **Step 3: Implementar el servicio**

Crear `api/app/services/cortes_diarios.py`:

```python
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.data.cortes_diarios import CorteDiario, CorteMetodoPago
from app.data.gastos import Gasto
from app.data.metodos_pago import MetodoPago
from app.data.pagos import Pago
from app.data.tickets import Ticket


def _rango_del_dia(fecha: date) -> tuple[datetime, datetime]:
    inicio = datetime.combine(fecha, time.min, tzinfo=timezone.utc)
    fin = datetime.combine(fecha, time.max, tzinfo=timezone.utc)
    return inicio, fin


def _calcular_totales(db: Session, fecha: date) -> dict:
    inicio, fin = _rango_del_dia(fecha)

    tickets = (
        db.query(func.coalesce(func.sum(Ticket.total), 0), func.count(Ticket.id))
        .filter(Ticket.fecha_emision >= inicio, Ticket.fecha_emision <= fin)
        .one()
    )
    total_ventas, num_tickets = Decimal(tickets[0]), tickets[1]

    total_gastos = (
        db.query(func.coalesce(func.sum(Gasto.monto), 0))
        .filter(Gasto.fecha_gasto >= inicio, Gasto.fecha_gasto <= fin)
        .scalar()
    )
    total_gastos = Decimal(total_gastos)

    num_pedidos = (
        db.query(func.count(func.distinct(Ticket.id_pedido)))
        .filter(Ticket.fecha_emision >= inicio, Ticket.fecha_emision <= fin)
        .scalar()
    )

    desglose = (
        db.query(MetodoPago.id, func.coalesce(func.sum(Ticket.total), 0))
        .join(Pago, Pago.id_metodo == MetodoPago.id)
        .join(Ticket, Ticket.id == Pago.id_ticket)
        .filter(Ticket.fecha_emision >= inicio, Ticket.fecha_emision <= fin)
        .group_by(MetodoPago.id)
        .all()
    )

    return {
        "total_ventas": total_ventas,
        "total_gastos": total_gastos,
        "ganancia_neta": total_ventas - total_gastos,
        "num_pedidos": num_pedidos,
        "num_tickets": num_tickets,
        "desglose": [{"id_metodo_pago": id_metodo, "monto": Decimal(monto)} for id_metodo, monto in desglose],
    }


def generar_o_actualizar_corte(db: Session, fecha: date, id_usuario: int) -> CorteDiario:
    totales = _calcular_totales(db, fecha)

    corte = db.query(CorteDiario).filter(CorteDiario.fecha == fecha).first()
    if corte is None:
        corte = CorteDiario(fecha=fecha, id_usuario=id_usuario, **{
            k: v for k, v in totales.items() if k != "desglose"
        })
        db.add(corte)
        db.flush()
    else:
        for campo in ("total_ventas", "total_gastos", "ganancia_neta", "num_pedidos", "num_tickets"):
            setattr(corte, campo, totales[campo])
        corte.id_usuario = id_usuario
        db.query(CorteMetodoPago).filter(CorteMetodoPago.id_corte == corte.id).delete()
        db.flush()

    for fila in totales["desglose"]:
        db.add(CorteMetodoPago(id_corte=corte.id, id_metodo_pago=fila["id_metodo_pago"], monto=fila["monto"]))

    db.commit()
    db.refresh(corte)
    return corte


def obtener_corte(db: Session, fecha: date) -> CorteDiario | None:
    return (
        db.query(CorteDiario)
        .options(joinedload(CorteDiario.desglose_metodos).joinedload(CorteMetodoPago.metodo))
        .filter(CorteDiario.fecha == fecha)
        .first()
    )


def listar_cortes(db: Session, desde: date, hasta: date) -> list[CorteDiario]:
    return (
        db.query(CorteDiario)
        .filter(CorteDiario.fecha >= desde, CorteDiario.fecha <= hasta)
        .order_by(CorteDiario.fecha.desc())
        .all()
    )
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_cortes_diarios_service.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Commit**

```bash
git add api/app/services/cortes_diarios.py api/app/tests/test_cortes_diarios_service.py
git commit -m "feat(api): servicio de calculo y upsert del corte diario"
```

---

### Task 3: Modelos Pydantic + router `/api/cortes-diarios`

**Files:**
- Create: `api/app/models/cortes_diarios.py`
- Create: `api/app/routers/cortes_diarios.py`
- Modify: `api/app/main.py`
- Test: `api/app/tests/test_router_cortes_diarios.py`

**Interfaces:**
- Consumes: funciones del Task 2, `TokenData`/`get_current_user` (para tomar `id_usuario` del JWT del admin autenticado).
- Produces:
  - `POST /api/cortes-diarios?fecha=YYYY-MM-DD` (default hoy) → 200 `CorteDiarioOut`
  - `GET /api/cortes-diarios?desde=&hasta=` → 200 `list[CorteDiarioOut]`
  - `GET /api/cortes-diarios/{fecha}` → 200 `CorteDiarioOut` | 404

- [ ] **Step 1: Modelos Pydantic**

Crear `api/app/models/cortes_diarios.py`:

```python
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DesgloseMetodoPagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    metodo_pago: str
    monto: Decimal


class CorteDiarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date
    total_ventas: Decimal
    total_gastos: Decimal
    ganancia_neta: Decimal
    num_pedidos: int
    num_tickets: int
    generado_en: datetime
    desglose_metodos: list[DesgloseMetodoPagoOut]
```

Nota: `desglose_metodos` en el modelo SQLAlchemy expone `CorteMetodoPago` (con `.metodo.nombre`, no `.metodo_pago` directo) — Pydantic con `from_attributes=True` no resuelve `metodo_pago` automáticamente desde `metodo.nombre`. Para que serialice bien, usar un adaptador en el router (Step 3) que construya explícitamente `DesgloseMetodoPagoOut(metodo_pago=d.metodo.nombre, monto=d.monto)` en vez de confiar en la serialización automática de la relación completa.

- [ ] **Step 2: Escribir los tests que deben fallar**

Crear `api/app/tests/test_router_cortes_diarios.py`:

```python
from datetime import date, datetime, timezone
from decimal import Decimal

from app.core.constants import EstatusPedidoNombre, MetodoPagoNombre, RolNombre
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


def test_generar_corte_requiere_admin(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.CAJERO)
    respuesta = client.post(
        "/api/cortes-diarios?fecha=2026-06-15", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta.status_code == 403


def test_generar_y_consultar_corte(client, db_session, catalogos, mesa_libre, usuario_mesero):
    dia = datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc)
    pedido = Pedido(
        id_mesa=mesa_libre.id, id_usuario=usuario_mesero.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.ENTREGADO].id,
        fecha=dia, total=Decimal("80.00"),
    )
    db_session.add(pedido)
    db_session.flush()
    ticket = Ticket(subtotal=Decimal("80.00"), iva=Decimal("0"), total=Decimal("80.00"),
                     id_pedido=pedido.id, id_usuario=usuario_mesero.id, fecha_emision=dia)
    db_session.add(ticket)
    db_session.flush()
    db_session.add(Pago(monto_recibido=Decimal("80.00"), cambio=Decimal("0"), id_ticket=ticket.id,
                         id_metodo=catalogos["metodos_pago"][MetodoPagoNombre.EFECTIVO].id))
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta_post = client.post("/api/cortes-diarios?fecha=2026-06-15", headers={"Authorization": f"Bearer {token}"})
    assert respuesta_post.status_code == 200
    assert respuesta_post.json()["total_ventas"] == "80.00"

    respuesta_get = client.get("/api/cortes-diarios/2026-06-15", headers={"Authorization": f"Bearer {token}"})
    assert respuesta_get.status_code == 200

    respuesta_lista = client.get(
        "/api/cortes-diarios?desde=2026-06-01&hasta=2026-06-30", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta_lista.status_code == 200
    assert len(respuesta_lista.json()) == 1


def test_obtener_corte_no_generado_404(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get("/api/cortes-diarios/2099-01-01", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 404
```

- [ ] **Step 3: Correr los tests, verificar que fallan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_cortes_diarios.py -v`
Expected: FAIL con 404 en todas las rutas (el router no existe)

- [ ] **Step 4: Implementar el router**

Crear `api/app/routers/cortes_diarios.py`:

```python
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.db import get_db
from app.models.cortes_diarios import CorteDiarioOut, DesgloseMetodoPagoOut
from app.security.auth import TokenData, require_rol
from app.services.cortes_diarios import generar_o_actualizar_corte, listar_cortes, obtener_corte

router = APIRouter(prefix="/api/cortes-diarios", tags=["cortes-diarios"])

_solo_admin = require_rol(RolNombre.ADMINISTRADOR)


def _serializar(corte) -> CorteDiarioOut:
    return CorteDiarioOut(
        id=corte.id,
        fecha=corte.fecha,
        total_ventas=corte.total_ventas,
        total_gastos=corte.total_gastos,
        ganancia_neta=corte.ganancia_neta,
        num_pedidos=corte.num_pedidos,
        num_tickets=corte.num_tickets,
        generado_en=corte.generado_en,
        desglose_metodos=[
            DesgloseMetodoPagoOut(metodo_pago=d.metodo.nombre, monto=d.monto) for d in corte.desglose_metodos
        ],
    )


@router.post("", response_model=CorteDiarioOut)
def generar(
    fecha: date | None = None,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(_solo_admin),
) -> CorteDiarioOut:
    fecha = fecha or date.today()
    corte = generar_o_actualizar_corte(db, fecha, usuario.user_id)
    return _serializar(corte)


@router.get("", response_model=list[CorteDiarioOut])
def listar(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> list[CorteDiarioOut]:
    hasta = hasta or date.today()
    desde = desde or (hasta - timedelta(days=30))
    return [_serializar(c) for c in listar_cortes(db, desde, hasta)]


@router.get("/{fecha}", response_model=CorteDiarioOut)
def obtener(fecha: date, db: Session = Depends(get_db), _=Depends(_solo_admin)) -> CorteDiarioOut:
    corte = obtener_corte(db, fecha)
    if corte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay corte generado para esa fecha")
    return _serializar(corte)
```

**Importante:** verificar el nombre real del campo de `TokenData` que guarda el id del usuario autenticado (`user_id` es una suposición basada en la firma de `create_access_token(user_id=..., rol=...)` vista en los tests existentes — confirmar leyendo `api/app/security/auth.py` antes de asumirlo).

En `api/app/main.py`, agregar junto a los demás routers:

```python
from app.routers.cortes_diarios import router as cortes_diarios_router
```
```python
app.include_router(cortes_diarios_router)
```

- [ ] **Step 5: Correr los tests, verificar que pasan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_cortes_diarios.py -v`
Expected: PASS (3/3)

- [ ] **Step 6: Correr toda la suite de la API**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde

- [ ] **Step 7: Commit**

```bash
git add api/app/models/cortes_diarios.py api/app/routers/cortes_diarios.py api/app/main.py api/app/tests/test_router_cortes_diarios.py
git commit -m "feat(api): endpoints POST/GET /api/cortes-diarios"
```

---

### Task 4: Página "Corte diario" en web-admin

**Files:**
- Modify: `web-admin/app/api_client.py` (agregar `generar_corte_diario`, `listar_cortes_diarios`, `obtener_corte_diario`)
- Create: `web-admin/app/blueprints/cortes_diarios.py`
- Create: `web-admin/app/templates/corte_diario.html`
- Modify: `web-admin/app/templates/base.html` (nav link)
- Modify: `web-admin/app/__init__.py` (registrar blueprint)
- Test: `web-admin/tests/test_corte_diario.py`

**Interfaces:**
- Consumes: `POST/GET /api/cortes-diarios{,/{fecha}}` (Task 3).
- Produces: rutas `cortes_diarios.index` (GET `/corte-diario`), `cortes_diarios.generar` (POST `/corte-diario/generar`).

- [ ] **Step 1: Agregar funciones al api_client**

En `web-admin/app/api_client.py`:

```python
def generar_corte_diario(base_url: str, token: str, fecha: str | None = None) -> dict:
    params = {"fecha": fecha} if fecha else {}
    return _request("POST", base_url, "/api/cortes-diarios", token=token, params=params)


def listar_cortes_diarios(base_url: str, token: str, desde: str, hasta: str) -> list[dict]:
    return _request(
        "GET", base_url, "/api/cortes-diarios", token=token, params={"desde": desde, "hasta": hasta}
    )
```

- [ ] **Step 2: Escribir los tests que deben fallar**

Crear `web-admin/tests/test_corte_diario.py`:

```python
import importlib

import pytest
import responses

from app.blueprints.cortes_diarios import bp as cortes_bp

BASE_URL = "http://testserver"


@pytest.fixture()
def client(app):
    if "cortes_diarios" not in app.blueprints:
        app.register_blueprint(cortes_bp)
    for nombre in ("usuarios", "productos", "ingredientes", "recetas", "reportes", "categorias"):
        if nombre in app.blueprints:
            continue
        try:
            modulo = importlib.import_module(f"app.blueprints.{nombre}")
        except ImportError:
            continue
        app.register_blueprint(modulo.bp)
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_index_muestra_historial(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/cortes-diarios",
        json=[
            {
                "id": 1, "fecha": "2026-06-15", "total_ventas": "150.00", "total_gastos": "30.00",
                "ganancia_neta": "120.00", "num_pedidos": 2, "num_tickets": 2,
                "generado_en": "2026-06-15T23:00:00", "desglose_metodos": [],
            }
        ],
        status=200,
    )
    respuesta = client.get("/corte-diario")
    assert respuesta.status_code == 200
    assert b"150.00" in respuesta.data


@responses.activate
def test_generar_corte_de_hoy(client):
    _login_como_admin(client)
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/cortes-diarios",
        json={
            "id": 1, "fecha": "2026-07-03", "total_ventas": "0.00", "total_gastos": "0.00",
            "ganancia_neta": "0.00", "num_pedidos": 0, "num_tickets": 0,
            "generado_en": "2026-07-03T23:00:00", "desglose_metodos": [],
        },
        status=200,
    )
    respuesta = client.post("/corte-diario/generar", follow_redirects=False)
    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "POST"
```

- [ ] **Step 3: Correr los tests, verificar que fallan**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_corte_diario.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 4: Implementar el blueprint**

Crear `web-admin/app/blueprints/cortes_diarios.py`:

```python
from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import ApiError, generar_corte_diario, listar_cortes_diarios
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("cortes_diarios", __name__, url_prefix="/corte-diario")


@bp.route("")
@login_required
def index():
    token = current_token()
    base_url = api_base_url()
    hoy = date.today()
    cortes = listar_cortes_diarios(base_url, token, (hoy - timedelta(days=30)).isoformat(), hoy.isoformat())
    return render_template("corte_diario.html", cortes=cortes)


@bp.route("/generar", methods=["POST"])
@login_required
def generar():
    fecha = request.form.get("fecha") or None
    try:
        generar_corte_diario(api_base_url(), current_token(), fecha)
        flash("Corte diario generado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo generar el corte: {error.detail}", "error")
    return redirect(url_for("cortes_diarios.index"))
```

- [ ] **Step 5: Crear el template**

Crear `web-admin/app/templates/corte_diario.html`:

```html
{% extends "base.html" %}
{% block title %}Corte diario — Coffee Code Admin{% endblock %}
{% block content %}
<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-semibold text-starbucks">Corte diario</h1>
  <form action="{{ url_for('cortes_diarios.generar') }}" method="post" class="flex items-center gap-2">
    <input type="date" name="fecha" class="input-field !w-auto py-1.5">
    <button type="submit" class="btn btn-primary">Generar corte</button>
  </form>
</div>

<div class="card overflow-hidden">
  <table class="data-table">
    <thead>
      <tr>
        <th>Fecha</th>
        <th>Ventas</th>
        <th>Gastos</th>
        <th>Ganancia neta</th>
        <th># Tickets</th>
        <th>Generado</th>
      </tr>
    </thead>
    <tbody>
      {% for corte in cortes %}
      <tr>
        <td>{{ corte.fecha }}</td>
        <td>${{ "%.2f"|format(corte.total_ventas|float) }}</td>
        <td>${{ "%.2f"|format(corte.total_gastos|float) }}</td>
        <td>${{ "%.2f"|format(corte.ganancia_neta|float) }}</td>
        <td>{{ corte.num_tickets }}</td>
        <td>{{ corte.generado_en }}</td>
      </tr>
      {% else %}
      <tr><td colspan="6" class="text-black/58 text-sm p-5">Sin cortes generados en los últimos 30 días.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

- [ ] **Step 6: Registrar blueprint y nav link**

En `web-admin/app/__init__.py`:

```python
    from app.blueprints.cortes_diarios import bp as cortes_diarios_bp
```
```python
    app.register_blueprint(cortes_diarios_bp)
```

En `web-admin/app/templates/base.html`, agregar junto a los demás nav links:

```html
      <a href="{{ url_for('cortes_diarios.index') }}" class="nav-link {{ 'active' if request.endpoint and request.endpoint.startswith('cortes_diarios.') }}">Corte diario</a>
```

- [ ] **Step 7: Correr los tests, verificar que pasan**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_corte_diario.py -v`
Expected: PASS (2/2)

- [ ] **Step 8: Correr toda la suite de web-admin**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde

- [ ] **Step 9: Commit**

```bash
git add web-admin/app/api_client.py web-admin/app/blueprints/cortes_diarios.py web-admin/app/templates/corte_diario.html web-admin/app/templates/base.html web-admin/app/__init__.py web-admin/tests/test_corte_diario.py
git commit -m "feat(web-admin): pagina de corte diario con historial"
```

---

### Task 5: Postman

**Files:**
- Modify: `postman/coffee-code.postman_collection.json`

- [ ] **Step 1: Agregar una carpeta nueva "06 - Admin - Corte Diario"** con 3 requests: "Generar Corte" (POST `{{base_url}}/api/cortes-diarios?fecha=2026-06-15`), "Listar Cortes" (GET `{{base_url}}/api/cortes-diarios?desde=2026-06-01&hasta=2026-06-30`), "Obtener Corte" (GET `{{base_url}}/api/cortes-diarios/2026-06-15`) — todas con header `Authorization: Bearer {{token_admin}}`, siguiendo el formato de la carpeta "05 - Admin - Reportes" ya existente.

- [ ] **Step 2: Validar JSON**

Run: `python -c "import json; json.load(open('postman/coffee-code.postman_collection.json', encoding='utf-8'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add postman/coffee-code.postman_collection.json
git commit -m "docs(postman): agregar requests de corte diario"
```
