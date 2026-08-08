# Cierre de cuenta, edición de pedidos y tickets — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesero puede editar un pedido mientras siga Pendiente, abrir varios pedidos concurrentes por mesa, y cerrar la cuenta (crea Ticket sin pago) antes de que Cajero cobre; Entregado queda bloqueado hasta que exista un Ticket pagado.

**Architecture:** Backend FastAPI: nuevos endpoints CRUD de items de pedido, endpoint de cierre de cuenta, gate real de pago en la transición a Entregado, contrato de `POST /ventas` cambia de "crea Ticket+Pago" a "adjunta Pago a un Ticket ya cerrado", nuevo `GET /tickets`. Mobile React Native: pantallas existentes (`DetalleScreen`, `MesasScreen`, `CajaScreen`, `PagoScreen`) se adaptan al nuevo flujo, una pantalla nueva (`PedidosMesaScreen`) lista los pedidos activos de una mesa.

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic + pytest (backend, DB Postgres real de test vía `TEST_DATABASE_URL`), React Native + Expo + jest (mobile, solo funciones puras de `api/*.js`; las pantallas se verifican manualmente contra Docker, mismo patrón que el resto del proyecto — ver `.superpowers/sdd/progress.md`).

## Global Constraints

- Español en nombres de tablas/campos/mensajes de error/commits (`CLAUDE.md`). Código interno (variables/funciones) puede ir en inglés o español, seguir el estilo ya usado en cada archivo (español en este proyecto).
- Un pedido nunca puede quedar con 0 items (invariante ya existente en `crear_pedido`, se extiende a `eliminar_item_pedido`).
- Descuento de inventario atómico al marcar Listo — no se toca en este plan, sigue igual.
- No se permiten pagos duplicados — el check ya existe (`Ticket.pago` no None), se reubica de "Pedido ya tiene ticket" a "Ticket ya tiene pago".
- JWT en `Authorization: Bearer {token}`, autorización por rol vía `require_rol(*roles)`.
- Commit tras cada task completa y revisada, no cada paso suelto.

---

## Backend

### Task 1: `GET /pedidos?mesa_id=` — filtro por mesa

**Files:**
- Modify: `api/app/routers/pedidos.py:39-54` (función `listar`)
- Test: `api/app/tests/test_router_pedidos.py` (nuevo archivo)

**Interfaces:**
- Produces: `GET /pedidos?mesa_id={int}&estado={str}` — combinable con el filtro `estado` ya existente. Usado por Task 12 (mobile).

- [ ] **Step 1: Escribir el test que falla**

```python
# api/app/tests/test_router_pedidos.py
from decimal import Decimal

from app.core.constants import EstatusPedidoNombre, RolNombre
from app.data.categorias import Categoria
from app.data.mesas import Mesa
from app.data.productos import Producto
from app.security.auth import create_access_token
from app.services.pedidos import crear_pedido
from app.models.pedidos import DetallePedidoCreate, PedidoCreate


def _token(catalogos, rol: str, user_id: int = 1) -> str:
    return create_access_token(user_id=user_id, rol=catalogos["roles"][rol].nombre)


def _crear_mesa_y_producto(db_session, catalogos):
    mesa = Mesa(numero_mesa=7, capacidad=2, id_estatus=catalogos["estatus_mesas"][EstatusPedidoNombre.PENDIENTE and "Libre" or "Libre"].id)
    db_session.add(mesa)
    categoria = Categoria(nombre="Bebidas", activo=True)
    db_session.add(categoria)
    db_session.flush()
    producto = Producto(nombre="Espresso", precio_venta=Decimal("30.00"), disponible=True, activo=True, id_categoria=categoria.id)
    db_session.add(producto)
    db_session.flush()
    return mesa, producto


def test_listar_pedidos_filtra_por_mesa_id(client, db_session, catalogos, usuario_mesero):
    mesa_1, producto = _crear_mesa_y_producto(db_session, catalogos)
    mesa_2 = Mesa(numero_mesa=8, capacidad=2, id_estatus=catalogos["estatus_mesas"]["Libre"].id)
    db_session.add(mesa_2)
    db_session.flush()

    crear_pedido(db_session, PedidoCreate(mesa_id=mesa_1.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    crear_pedido(db_session, PedidoCreate(mesa_id=mesa_2.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))

    token = _token(catalogos, RolNombre.MESERO)
    respuesta = client.get(f"/pedidos?mesa_id={mesa_1.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    ids_mesa = {p["id_mesa"] for p in respuesta.json()}
    assert ids_mesa == {mesa_1.id}
```

Simplifica el helper `_crear_mesa_y_producto`, quita la expresión ternaria confusa de `id_estatus` (era un descuido de redacción, usa directamente `catalogos["estatus_mesas"]["Libre"].id`):

```python
def _crear_mesa_y_producto(db_session, catalogos):
    mesa = Mesa(numero_mesa=7, capacidad=2, id_estatus=catalogos["estatus_mesas"]["Libre"].id)
    db_session.add(mesa)
    categoria = Categoria(nombre="Bebidas", activo=True)
    db_session.add(categoria)
    db_session.flush()
    producto = Producto(nombre="Espresso", precio_venta=Decimal("30.00"), disponible=True, activo=True, id_categoria=categoria.id)
    db_session.add(producto)
    db_session.flush()
    return mesa, producto
```

- [ ] **Step 2: Correr el test, verificar que falla**

Run: `cd api && python -m pytest app/tests/test_router_pedidos.py -v`
Expected: FAIL — devuelve ambos pedidos (2 items), no solo el de `mesa_1.id` (assert de `ids_mesa == {mesa_1.id}` falla porque hoy no existe el filtro).

- [ ] **Step 3: Implementar el filtro**

En `api/app/routers/pedidos.py`, modificar `listar`:

```python
@router.get("", response_model=list[PedidoOut])
def listar(
    estado: str | None = None,
    mesa_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _=Depends(
        require_rol(
            RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR
        )
    ),
) -> list[Pedido]:
    query = db.query(Pedido).options(*_PEDIDO_LOAD_OPTIONS)
    if estado:
        query = query.join(EstatusPedido).filter(EstatusPedido.nombre == estado)
    if mesa_id is not None:
        query = query.filter(Pedido.id_mesa == mesa_id)
    return query.order_by(Pedido.fecha.asc()).offset(offset).limit(limit).all()
```

- [ ] **Step 4: Correr el test, verificar que pasa**

Run: `cd api && python -m pytest app/tests/test_router_pedidos.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/pedidos.py api/app/tests/test_router_pedidos.py
git commit -m "feat(api): filtrar GET /pedidos por mesa_id"
```

---

### Task 2: Editar pedido Pendiente — agregar item

**Files:**
- Modify: `api/app/models/pedidos.py` (agregar `ItemPedidoUpdate`, usado también en Task 3)
- Modify: `api/app/services/pedidos.py` (nueva función `agregar_item_pedido` + helper `_validar_pedido_editable`)
- Modify: `api/app/routers/pedidos.py` (nuevo endpoint `POST /pedidos/{id}/items`)
- Test: `api/app/tests/test_services_pedidos.py`

**Interfaces:**
- Consumes: `EstatusCocinaNombre`, `_get_estatus_cocina_por_nombre` ya definidos en `services/pedidos.py`.
- Produces: `agregar_item_pedido(db: Session, pedido: Pedido, datos: DetallePedidoCreate) -> Pedido`, endpoint `POST /pedidos/{pedido_id}/items` (Mesero/Admin) devolviendo `PedidoOut`. `_validar_pedido_editable(pedido: Pedido) -> None` reutilizado por Task 3.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `api/app/tests/test_services_pedidos.py` (usa los fixtures `categoria`, `producto_sin_receta` ya definidos en ese archivo):

```python
from app.services.pedidos import agregar_item_pedido


def test_agregar_item_a_pedido_pendiente(db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)

    pedido = agregar_item_pedido(
        db_session, pedido, DetallePedidoCreate(id_producto=producto_sin_receta.id, cantidad=3)
    )

    assert len(pedido.detalle) == 2
    assert pedido.detalle[1].cantidad == 3


def test_agregar_item_a_pedido_no_pendiente_devuelve_409(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta
):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)

    with pytest.raises(HTTPException) as exc_info:
        agregar_item_pedido(db_session, pedido, DetallePedidoCreate(id_producto=producto_sin_receta.id, cantidad=1))

    assert exc_info.value.status_code == 409


def test_agregar_item_producto_no_disponible_devuelve_409(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta, producto_no_disponible
):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)

    with pytest.raises(HTTPException) as exc_info:
        agregar_item_pedido(db_session, pedido, DetallePedidoCreate(id_producto=producto_no_disponible.id, cantidad=1))

    assert exc_info.value.status_code == 409
```

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd api && python -m pytest app/tests/test_services_pedidos.py -k agregar_item -v`
Expected: FAIL con `ImportError: cannot import name 'agregar_item_pedido'`

- [ ] **Step 3: Implementar**

En `api/app/models/pedidos.py`, agregar al final del archivo:

```python
class ItemPedidoUpdate(BaseModel):
    cantidad: int | None = Field(default=None, ge=1)
    especificaciones: str | None = None
```

En `api/app/services/pedidos.py`, agregar tras `_get_estatus_cocina_por_nombre` (antes de `crear_pedido`):

```python
def _validar_pedido_editable(pedido: Pedido) -> None:
    if pedido.estatus.nombre != EstatusPedidoNombre.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede editar un pedido que ya está en preparación",
        )
```

Y tras `crear_pedido`, agregar:

```python
def agregar_item_pedido(db: Session, pedido: Pedido, datos: DetallePedidoCreate) -> Pedido:
    _validar_pedido_editable(pedido)

    producto = db.query(Producto).filter(Producto.id == datos.id_producto).first()
    if not producto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    if not producto.disponible:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Producto no disponible: {producto.nombre}"
        )

    estatus_cocina_pendiente = _get_estatus_cocina_por_nombre(db, EstatusCocinaNombre.PENDIENTE)
    pedido.detalle.append(
        DetallePedido(
            id_producto=producto.id,
            cantidad=datos.cantidad,
            especificaciones=datos.especificaciones,
            precio_unitario=producto.precio_venta,
            id_estatus=estatus_cocina_pendiente.id,
        )
    )
    db.commit()
    db.refresh(pedido)
    return pedido
```

Necesita el import `DetallePedidoCreate` ya presente (`from app.models.pedidos import PedidoCreate` → cambiar a `from app.models.pedidos import DetallePedidoCreate, PedidoCreate`).

En `api/app/routers/pedidos.py`, actualizar el import de servicios y agregar el endpoint:

```python
from app.services.pedidos import agregar_item_pedido, cambiar_estado_pedido, crear_pedido
```

```python
@router.post("/{pedido_id}/items", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def agregar_item(
    pedido_id: int,
    datos: DetallePedidoCreate,
    db: Session = Depends(get_db),
    _=Depends(require_rol(RolNombre.MESERO, RolNombre.ADMINISTRADOR)),
) -> Pedido:
    pedido = _get_pedido_o_404(db, pedido_id)
    agregar_item_pedido(db, pedido, datos)
    return _get_pedido_o_404(db, pedido_id)
```

Y el import `from app.models.pedidos import CambioEstadoPedido, PedidoOut` → `from app.models.pedidos import CambioEstadoPedido, DetallePedidoCreate, PedidoOut`.

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && python -m pytest app/tests/test_services_pedidos.py -v`
Expected: PASS (todos, incluyendo los preexistentes — nada debe romperse)

- [ ] **Step 5: Commit**

```bash
git add api/app/models/pedidos.py api/app/services/pedidos.py api/app/routers/pedidos.py api/app/tests/test_services_pedidos.py
git commit -m "feat(api): permitir agregar items a un pedido Pendiente"
```

---

### Task 3: Editar pedido Pendiente — actualizar y eliminar item

**Files:**
- Modify: `api/app/services/pedidos.py` (`actualizar_item_pedido`, `eliminar_item_pedido`, `_get_item_o_404`)
- Modify: `api/app/routers/pedidos.py` (`PUT`/`DELETE /pedidos/{id}/items/{item_id}`)
- Test: `api/app/tests/test_services_pedidos.py`

**Interfaces:**
- Consumes: `_validar_pedido_editable` de Task 2, `ItemPedidoUpdate` de Task 2.
- Produces: `actualizar_item_pedido(db, pedido, item_id, datos: ItemPedidoUpdate) -> Pedido`, `eliminar_item_pedido(db, pedido, item_id) -> Pedido`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `api/app/tests/test_services_pedidos.py`:

```python
from app.models.pedidos import ItemPedidoUpdate
from app.services.pedidos import actualizar_item_pedido, eliminar_item_pedido


def test_actualizar_cantidad_de_item_pendiente(db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta, cantidad=1)
    item_id = pedido.detalle[0].id

    pedido = actualizar_item_pedido(db_session, pedido, item_id, ItemPedidoUpdate(cantidad=5))

    assert pedido.detalle[0].cantidad == 5


def test_actualizar_item_inexistente_devuelve_404(db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)

    with pytest.raises(HTTPException) as exc_info:
        actualizar_item_pedido(db_session, pedido, 99999, ItemPedidoUpdate(cantidad=2))

    assert exc_info.value.status_code == 404


def test_eliminar_item_deja_al_menos_uno(db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta, cantidad=1)
    pedido = agregar_item_pedido(db_session, pedido, DetallePedidoCreate(id_producto=producto_sin_receta.id, cantidad=1))
    item_a_borrar = pedido.detalle[0].id

    pedido = eliminar_item_pedido(db_session, pedido, item_a_borrar)

    assert len(pedido.detalle) == 1


def test_eliminar_ultimo_item_devuelve_409(db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta, cantidad=1)
    item_id = pedido.detalle[0].id

    with pytest.raises(HTTPException) as exc_info:
        eliminar_item_pedido(db_session, pedido, item_id)

    assert exc_info.value.status_code == 409


def test_editar_item_de_pedido_en_preparacion_devuelve_409(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta
):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta, cantidad=1)
    item_id = pedido.detalle[0].id
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)

    with pytest.raises(HTTPException) as exc_info:
        actualizar_item_pedido(db_session, pedido, item_id, ItemPedidoUpdate(cantidad=2))

    assert exc_info.value.status_code == 409
```

`agregar_item_pedido` y `DetallePedidoCreate` ya están importados en el archivo desde Task 2.

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd api && python -m pytest app/tests/test_services_pedidos.py -k "actualizar_item or eliminar_item or editar_item" -v`
Expected: FAIL con `ImportError`

- [ ] **Step 3: Implementar**

En `api/app/services/pedidos.py`, agregar tras `agregar_item_pedido`:

```python
def _get_item_o_404(pedido: Pedido, item_id: int) -> DetallePedido:
    for item in pedido.detalle:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ítem no encontrado en este pedido")


def actualizar_item_pedido(db: Session, pedido: Pedido, item_id: int, datos: "ItemPedidoUpdate") -> Pedido:
    _validar_pedido_editable(pedido)
    item = _get_item_o_404(pedido, item_id)

    cambios = datos.model_dump(exclude_unset=True)
    if "cantidad" in cambios:
        item.cantidad = cambios["cantidad"]
    if "especificaciones" in cambios:
        item.especificaciones = cambios["especificaciones"]

    db.commit()
    db.refresh(pedido)
    return pedido


def eliminar_item_pedido(db: Session, pedido: Pedido, item_id: int) -> Pedido:
    _validar_pedido_editable(pedido)
    item = _get_item_o_404(pedido, item_id)

    if len(pedido.detalle) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El pedido debe tener al menos un ítem"
        )

    pedido.detalle.remove(item)
    db.delete(item)
    db.commit()
    db.refresh(pedido)
    return pedido
```

Agregar el import de `ItemPedidoUpdate` al inicio del archivo: `from app.models.pedidos import DetallePedidoCreate, ItemPedidoUpdate, PedidoCreate`. Cambiar la anotación de tipo `datos: "ItemPedidoUpdate"` (string) por `datos: ItemPedidoUpdate` directo, ya que ahora está importado.

En `api/app/routers/pedidos.py`:

```python
from app.models.pedidos import CambioEstadoPedido, DetallePedidoCreate, ItemPedidoUpdate, PedidoOut
from app.services.pedidos import (
    actualizar_item_pedido,
    agregar_item_pedido,
    cambiar_estado_pedido,
    crear_pedido,
    eliminar_item_pedido,
)
```

```python
@router.put("/{pedido_id}/items/{item_id}", response_model=PedidoOut)
def actualizar_item(
    pedido_id: int,
    item_id: int,
    datos: ItemPedidoUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_rol(RolNombre.MESERO, RolNombre.ADMINISTRADOR)),
) -> Pedido:
    pedido = _get_pedido_o_404(db, pedido_id)
    actualizar_item_pedido(db, pedido, item_id, datos)
    return _get_pedido_o_404(db, pedido_id)


@router.delete("/{pedido_id}/items/{item_id}", response_model=PedidoOut)
def eliminar_item(
    pedido_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_rol(RolNombre.MESERO, RolNombre.ADMINISTRADOR)),
) -> Pedido:
    pedido = _get_pedido_o_404(db, pedido_id)
    eliminar_item_pedido(db, pedido, item_id)
    return _get_pedido_o_404(db, pedido_id)
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && python -m pytest app/tests/test_services_pedidos.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add api/app/services/pedidos.py api/app/routers/pedidos.py api/app/tests/test_services_pedidos.py
git commit -m "feat(api): permitir actualizar y eliminar items de un pedido Pendiente"
```

---

### Task 4: `services/tickets.py` + `POST /pedidos/{id}/cerrar-cuenta`

**Files:**
- Create: `api/app/services/tickets.py`
- Modify: `api/app/models/ventas.py:27-36` (`TicketOut.pago` pasa a opcional)
- Modify: `api/app/routers/pedidos.py` (nuevo endpoint)
- Test: `api/app/tests/test_services_tickets.py` (nuevo archivo)

**Interfaces:**
- Produces: `calcular_totales(pedido: Pedido) -> tuple[Decimal, Decimal, Decimal]` (subtotal, iva, total — reutilizado por Task 6). `cerrar_cuenta(db: Session, pedido: Pedido, usuario_id: int) -> Ticket`. Endpoint `POST /pedidos/{pedido_id}/cerrar-cuenta` (Mesero/Admin) devolviendo `TicketOut` con `pago: null`.

- [ ] **Step 1: Escribir el test que falla**

```python
# api/app/tests/test_services_tickets.py
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.constants import EstatusPedidoNombre
from app.data.categorias import Categoria
from app.data.productos import Producto
from app.models.pedidos import DetallePedidoCreate, PedidoCreate
from app.services.pedidos import cambiar_estado_pedido, crear_pedido
from app.services.tickets import cerrar_cuenta


@pytest.fixture()
def categoria(db_session):
    cat = Categoria(nombre="Bebidas", activo=True)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def producto(db_session, categoria):
    producto = Producto(nombre="Cafe Americano", precio_venta=Decimal("35.00"), disponible=True, activo=True, id_categoria=categoria.id)
    db_session.add(producto)
    db_session.flush()
    return producto


def _pedido_listo(db_session, mesa, usuario, producto, cantidad=2):
    pedido = crear_pedido(
        db_session,
        PedidoCreate(mesa_id=mesa.id, usuario_id=usuario.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=cantidad)]),
    )
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    return pedido


def test_cerrar_cuenta_calcula_totales_y_no_crea_pago(db_session, catalogos, mesa_libre, usuario_mesero, producto):
    pedido = _pedido_listo(db_session, mesa_libre, usuario_mesero, producto, cantidad=2)

    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    # subtotal = 2 * 35.00 = 70.00 ; iva = 70 * 0.16 = 11.20 ; total = 81.20
    assert ticket.subtotal == Decimal("70.00")
    assert ticket.iva == Decimal("11.20")
    assert ticket.total == Decimal("81.20")
    assert ticket.pago is None


def test_cerrar_cuenta_de_pedido_no_listo_devuelve_409(db_session, catalogos, mesa_libre, usuario_mesero, producto):
    pedido = crear_pedido(
        db_session,
        PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]),
    )

    with pytest.raises(HTTPException) as exc_info:
        cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    assert exc_info.value.status_code == 409


def test_cerrar_cuenta_dos_veces_devuelve_409(db_session, catalogos, mesa_libre, usuario_mesero, producto):
    pedido = _pedido_listo(db_session, mesa_libre, usuario_mesero, producto)
    cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    with pytest.raises(HTTPException) as exc_info:
        cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    assert exc_info.value.status_code == 409
```

- [ ] **Step 2: Correr el test, verificar que falla**

Run: `cd api && python -m pytest app/tests/test_services_tickets.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.tickets'`

- [ ] **Step 3: Implementar**

Crear `api/app/services/tickets.py`:

```python
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import EstatusPedidoNombre
from app.data.pedidos import Pedido
from app.data.tickets import Ticket


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_totales(pedido: Pedido) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum((d.precio_unitario * d.cantidad for d in pedido.detalle), Decimal("0"))
    iva = _redondear(subtotal * Decimal(str(settings.iva_rate)))
    total = _redondear(subtotal + iva)
    return _redondear(subtotal), iva, total


def cerrar_cuenta(db: Session, pedido: Pedido, usuario_id: int) -> Ticket:
    if pedido.estatus.nombre != EstatusPedidoNombre.LISTO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede cerrar la cuenta de un pedido Listo",
        )

    ticket_existente = db.query(Ticket).filter(Ticket.id_pedido == pedido.id).first()
    if ticket_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La cuenta de este pedido ya fue cerrada"
        )

    subtotal, iva, total = calcular_totales(pedido)
    ticket = Ticket(subtotal=subtotal, iva=iva, total=total, id_pedido=pedido.id, id_usuario=usuario_id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket
```

En `api/app/models/ventas.py`, cambiar:

```python
class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subtotal: Decimal
    iva: Decimal
    total: Decimal
    fecha_emision: datetime
    id_pedido: int
    id_usuario: int
    pago: PagoOut | None = None
```

En `api/app/routers/pedidos.py`, agregar import y endpoint:

```python
from app.models.ventas import TicketOut
from app.security.auth import TokenData, require_rol
from app.services.tickets import cerrar_cuenta
```

(nota: `require_rol` ya está importado sin `TokenData` — agregar `TokenData` al import existente `from app.security.auth import require_rol` → `from app.security.auth import TokenData, require_rol`)

```python
@router.post("/{pedido_id}/cerrar-cuenta", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def cerrar_cuenta_endpoint(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(require_rol(RolNombre.MESERO, RolNombre.ADMINISTRADOR)),
):
    pedido = _get_pedido_o_404(db, pedido_id)
    return cerrar_cuenta(db, pedido, usuario_id=usuario.user_id)
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && python -m pytest app/tests/test_services_tickets.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/app/services/tickets.py api/app/models/ventas.py api/app/routers/pedidos.py api/app/tests/test_services_tickets.py
git commit -m "feat(api): endpoint para que Mesero cierre la cuenta de un pedido Listo"
```

---

### Task 5: Gate real de pago en la transición a Entregado

**Files:**
- Modify: `api/app/services/pedidos.py:151-197` (`cambiar_estado_pedido`)
- Test: `api/app/tests/test_services_pedidos.py`

**Interfaces:**
- Consumes: `Ticket` de `app.data.tickets`, `cerrar_cuenta` de Task 4 (usado en los tests, no en la implementación).
- Produces: `cambiar_estado_pedido` ahora lanza 409 si se intenta pasar a `Entregado` sin un `Ticket` con `Pago`. Este es el fix del bug real #4.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `api/app/tests/test_services_pedidos.py`:

```python
from app.data.pagos import Pago
from app.data.tickets import Ticket
from app.services.tickets import cerrar_cuenta


def test_entregar_sin_cerrar_cuenta_devuelve_409(db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta):
    """Regresión directa del hallazgo #4: Listo -> Entregado no exigía pago."""
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)

    with pytest.raises(HTTPException) as exc_info:
        cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)

    assert exc_info.value.status_code == 409


def test_entregar_con_cuenta_cerrada_pero_sin_pagar_devuelve_409(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta
):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    with pytest.raises(HTTPException) as exc_info:
        cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)

    assert exc_info.value.status_code == 409


def test_entregar_con_ticket_pagado_funciona(
    db_session, catalogos, mesa_libre, usuario_mesero, producto_sin_receta
):
    pedido = _crear_pedido_simple(db_session, mesa_libre, usuario_mesero, producto_sin_receta)
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)
    ticket.pago = Pago(
        monto_recibido=ticket.total, cambio=Decimal("0.00"), id_metodo=catalogos["metodos_pago"]["Efectivo"].id
    )
    db_session.commit()

    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)

    assert pedido.estatus.nombre == EstatusPedidoNombre.ENTREGADO
```

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd api && python -m pytest app/tests/test_services_pedidos.py -k entregar -v`
Expected: `test_entregar_sin_cerrar_cuenta_devuelve_409` y `test_entregar_con_cuenta_cerrada_pero_sin_pagar_devuelve_409` FALLAN (hoy la transición se permite sin check); `test_entregar_con_ticket_pagado_funciona` PASA de casualidad (no hay gate todavía).

- [ ] **Step 3: Implementar el gate**

En `api/app/services/pedidos.py`, agregar el import `from app.data.tickets import Ticket` al bloque de imports, y modificar `cambiar_estado_pedido`:

```python
def cambiar_estado_pedido(db: Session, pedido: Pedido, nuevo_estatus_nombre: str) -> tuple[Pedido, list[str]]:
    estatus_actual_nombre = pedido.estatus.nombre
    permitidos = TRANSICIONES_PEDIDO_VALIDAS.get(estatus_actual_nombre, set())

    if nuevo_estatus_nombre not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Transición inválida: no se puede pasar de '{estatus_actual_nombre}' "
                f"a '{nuevo_estatus_nombre}'"
            ),
        )

    if nuevo_estatus_nombre == EstatusPedidoNombre.ENTREGADO:
        ticket = (
            db.query(Ticket)
            .options(joinedload(Ticket.pago))
            .filter(Ticket.id_pedido == pedido.id)
            .first()
        )
        if not ticket or not ticket.pago:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede entregar un pedido sin cobrar",
            )

    nuevo_estatus = _get_estatus_pedido_por_nombre(db, nuevo_estatus_nombre)
    # ... resto de la función sin cambios
```

(El resto del cuerpo de la función, desde `alertas_stock_bajo: list[str] = []` en adelante, queda exactamente igual — solo se inserta el bloque de gate entre la validación de transición y `nuevo_estatus = _get_estatus_pedido_por_nombre(...)`.)

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && python -m pytest app/tests/test_services_pedidos.py -v`
Expected: PASS (todos, incluyendo los preexistentes de `Entregado` que ya cerraban cuenta a mano — revisar si alguno rompe, ver Step 4.1)

- [ ] **Step 4.1: Actualizar tests preexistentes que asumían Entregado sin pago**

`test_entregado_libera_mesa_cuando_no_hay_mas_pedidos_activos`, `test_entregado_no_libera_mesa_si_hay_otro_pedido_activo` y `test_entregado_libera_mesa_con_autoflush_desactivado` (ya existentes en el archivo) marcan `Entregado` sin cerrar cuenta ni pagar — ahora fallarán con 409. Actualizar cada uno agregando, antes de la línea `cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.ENTREGADO)` (o `pedido_1` según el test), estas líneas:

```python
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)
    ticket.pago = Pago(
        monto_recibido=ticket.total, cambio=Decimal("0.00"), id_metodo=catalogos["metodos_pago"]["Efectivo"].id
    )
    db_session.commit()
```

(sustituir `pedido` por `pedido_1` en `test_entregado_no_libera_mesa_si_hay_otro_pedido_activo`). Agregar los imports `from app.data.pagos import Pago` y `from app.services.tickets import cerrar_cuenta` al inicio del archivo si no están ya (deberían estar tras el Step 1 de este Task).

Run de nuevo: `cd api && python -m pytest app/tests/test_services_pedidos.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add api/app/services/pedidos.py api/app/tests/test_services_pedidos.py
git commit -m "fix(api): exigir Ticket pagado antes de marcar un pedido Entregado"
```

---

### Task 6: `POST /ventas` adjunta Pago a un Ticket ya cerrado

**Files:**
- Modify: `api/app/models/ventas.py:7-10` (`VentaCreate`)
- Modify: `api/app/services/ventas.py` (reescribir `registrar_venta`)
- Modify: `api/app/tests/test_services_ventas.py` (actualizar contrato)

**Interfaces:**
- Consumes: `cerrar_cuenta` de Task 4 (usado en los tests para preparar el Ticket).
- Produces: `registrar_venta(db, datos: VentaCreate, usuario_id) -> Ticket` ahora recibe `datos.ticket_id` en vez de `datos.pedido_id`. El router `caja.py` no cambia de firma (sigue pasando `datos` completo), solo cambia el shape del body que el cliente manda.

- [ ] **Step 1: Reescribir los tests existentes (definen el contrato nuevo)**

Reemplazar el contenido completo de `api/app/tests/test_services_ventas.py`:

```python
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.constants import EstatusPedidoNombre, MetodoPagoNombre
from app.data.categorias import Categoria
from app.data.productos import Producto
from app.models.pedidos import DetallePedidoCreate, PedidoCreate
from app.models.ventas import VentaCreate
from app.services.pedidos import cambiar_estado_pedido, crear_pedido
from app.services.tickets import cerrar_cuenta
from app.services.ventas import registrar_venta


@pytest.fixture()
def categoria(db_session):
    cat = Categoria(nombre="Bebidas", activo=True)
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture()
def producto(db_session, categoria):
    producto = Producto(nombre="Cafe Americano", precio_venta=Decimal("35.00"), disponible=True, activo=True, id_categoria=categoria.id)
    db_session.add(producto)
    db_session.flush()
    return producto


@pytest.fixture()
def ticket_cuenta_cerrada(db_session, catalogos, mesa_libre, usuario_mesero, producto):
    pedido = crear_pedido(
        db_session,
        PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=2)]),
    )
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    return cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)


def test_registrar_venta_calcula_cambio_y_marca_total_del_pedido(db_session, catalogos, ticket_cuenta_cerrada):
    # ticket.total ya viene calculado por cerrar_cuenta: 81.20
    datos = VentaCreate(ticket_id=ticket_cuenta_cerrada.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00"))

    ticket = registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    assert ticket.total == Decimal("81.20")
    assert ticket.pago.monto_recibido == Decimal("100.00")
    assert ticket.pago.cambio == Decimal("18.80")

    db_session.refresh(ticket)
    pedido = db_session.get.__self__  # no-op placeholder removed below


def test_registrar_venta_rechaza_monto_insuficiente(db_session, catalogos, ticket_cuenta_cerrada):
    datos = VentaCreate(ticket_id=ticket_cuenta_cerrada.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("10.00"))

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    assert exc_info.value.status_code == 400


def test_registrar_venta_bloquea_pago_duplicado(db_session, catalogos, ticket_cuenta_cerrada):
    datos = VentaCreate(ticket_id=ticket_cuenta_cerrada.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00"))
    registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    assert exc_info.value.status_code == 409


def test_registrar_venta_metodo_pago_invalido_devuelve_400(db_session, catalogos, ticket_cuenta_cerrada):
    datos = VentaCreate(ticket_id=ticket_cuenta_cerrada.id, metodo_pago="Bitcoin", monto=Decimal("100.00"))

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    assert exc_info.value.status_code == 400


def test_registrar_venta_ticket_inexistente_devuelve_404(db_session, catalogos):
    datos = VentaCreate(ticket_id=99999, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("10.00"))

    with pytest.raises(HTTPException) as exc_info:
        registrar_venta(db_session, datos, usuario_id=1)

    assert exc_info.value.status_code == 404
```

Quitar la línea placeholder `pedido = db_session.get.__self__ ...` del primer test (fue un error de redacción — el test correcto es solo hasta `assert ticket.pago.cambio == Decimal("18.80")`; agregar en su lugar una verificación real del `total` del pedido):

```python
def test_registrar_venta_calcula_cambio_y_marca_total_del_pedido(db_session, catalogos, ticket_cuenta_cerrada):
    from app.data.pedidos import Pedido

    datos = VentaCreate(ticket_id=ticket_cuenta_cerrada.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00"))

    ticket = registrar_venta(db_session, datos, usuario_id=ticket_cuenta_cerrada.id_usuario)

    assert ticket.total == Decimal("81.20")
    assert ticket.pago.monto_recibido == Decimal("100.00")
    assert ticket.pago.cambio == Decimal("18.80")

    pedido = db_session.query(Pedido).filter(Pedido.id == ticket_cuenta_cerrada.id_pedido).first()
    assert pedido.total == Decimal("81.20")
```

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd api && python -m pytest app/tests/test_services_ventas.py -v`
Expected: FAIL — `VentaCreate` no acepta `ticket_id` todavía (`ValidationError`).

- [ ] **Step 3: Implementar**

En `api/app/models/ventas.py`, cambiar:

```python
class VentaCreate(BaseModel):
    ticket_id: int
    metodo_pago: str
    monto: Decimal = Field(gt=0)
```

Reescribir `api/app/services/ventas.py` completo:

```python
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.data.metodos_pago import MetodoPago
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.models.ventas import VentaCreate


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def registrar_venta(db: Session, datos: VentaCreate, usuario_id: int) -> Ticket:
    ticket = (
        db.query(Ticket)
        .options(joinedload(Ticket.pago))
        .filter(Ticket.id == datos.ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado")

    if ticket.pago:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El ticket ya tiene un pago registrado"
        )

    metodo = db.query(MetodoPago).filter(MetodoPago.nombre == datos.metodo_pago).first()
    if not metodo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Método de pago inválido: '{datos.metodo_pago}'",
        )

    if datos.monto < ticket.total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El monto recibido ({datos.monto}) es insuficiente para el total ({ticket.total})",
        )

    ticket.pago = Pago(
        monto_recibido=datos.monto,
        cambio=_redondear(datos.monto - ticket.total),
        id_metodo=metodo.id,
    )

    pedido = db.query(Pedido).filter(Pedido.id == ticket.id_pedido).first()
    pedido.total = ticket.total

    db.commit()
    db.refresh(ticket)
    return ticket
```

`usuario_id` queda sin uso dentro de la función (el usuario que cobra no se guarda en el `Ticket`, que ya registró `id_usuario` del Mesero que cerró la cuenta) — se mantiene en la firma porque `routers/caja.py` ya lo pasa y podría usarse a futuro para auditoría del cobro; no se elimina el parámetro para no romper el router en este mismo commit.

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && python -m pytest app/tests/test_services_ventas.py -v`
Expected: PASS

- [ ] **Step 5: Correr la suite completa del backend**

Run: `cd api && python -m pytest -v`
Expected: PASS (todos — confirma que `routers/caja.py` sigue funcionando con el nuevo shape de `VentaCreate`, ya que solo cambia el JSON body, no la firma del endpoint)

- [ ] **Step 6: Commit**

```bash
git add api/app/models/ventas.py api/app/services/ventas.py api/app/tests/test_services_ventas.py
git commit -m "feat(api): POST /ventas adjunta pago a un ticket ya cerrado en vez de crear ticket+pago juntos"
```

---

### Task 7: `GET /tickets` — historial

**Files:**
- Create: `api/app/routers/tickets.py`
- Modify: `api/app/main.py` (registrar el router)
- Test: `api/app/tests/test_router_tickets.py` (nuevo archivo)

**Interfaces:**
- Consumes: `TicketOut` de Task 4, `cerrar_cuenta`/`registrar_venta` de Tasks 4/6 (usados en los tests para preparar datos).
- Produces: `GET /tickets?pagado={bool}` — Mesero ve solo tickets de pedidos que él mismo creó, Cajero/Admin ven todos.

- [ ] **Step 1: Escribir el test que falla**

```python
# api/app/tests/test_router_tickets.py
from decimal import Decimal

from app.core.constants import EstatusPedidoNombre, MetodoPagoNombre, RolNombre
from app.data.categorias import Categoria
from app.data.productos import Producto
from app.data.usuarios import Usuario
from app.models.pedidos import DetallePedidoCreate, PedidoCreate
from app.models.ventas import VentaCreate
from app.security.auth import create_access_token, hash_password
from app.services.pedidos import cambiar_estado_pedido, crear_pedido
from app.services.tickets import cerrar_cuenta
from app.services.ventas import registrar_venta


def _token(user_id: int, rol: str) -> str:
    return create_access_token(user_id=user_id, rol=rol)


def _crear_producto(db_session):
    categoria = Categoria(nombre="Bebidas", activo=True)
    db_session.add(categoria)
    db_session.flush()
    producto = Producto(nombre="Espresso", precio_venta=Decimal("30.00"), disponible=True, activo=True, id_categoria=categoria.id)
    db_session.add(producto)
    db_session.flush()
    return producto


def _otro_mesero(db_session, catalogos):
    usuario = Usuario(
        nombre="Otro",
        apellido_paterno="Mesero",
        correo_electronico="otro.mesero@coffeecode.com",
        password_hash=hash_password("Test1234!"),
        id_rol=catalogos["roles"][RolNombre.MESERO].id,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def test_mesero_solo_ve_sus_propios_tickets(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    otro_mesero = _otro_mesero(db_session, catalogos)

    pedido_propio = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido_propio, EstatusPedidoNombre.EN_PREPARACION)
    pedido_propio, _ = cambiar_estado_pedido(db_session, pedido_propio, EstatusPedidoNombre.LISTO)
    cerrar_cuenta(db_session, pedido_propio, usuario_id=usuario_mesero.id)

    from app.data.mesas import Mesa
    mesa_2 = Mesa(numero_mesa=2, capacidad=4, id_estatus=catalogos["estatus_mesas"]["Libre"].id)
    db_session.add(mesa_2)
    db_session.flush()
    pedido_ajeno = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_2.id, usuario_id=otro_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido_ajeno, EstatusPedidoNombre.EN_PREPARACION)
    pedido_ajeno, _ = cambiar_estado_pedido(db_session, pedido_ajeno, EstatusPedidoNombre.LISTO)
    cerrar_cuenta(db_session, pedido_ajeno, usuario_id=otro_mesero.id)

    token = _token(usuario_mesero.id, RolNombre.MESERO)
    respuesta = client.get("/tickets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    ids_pedido = {t["id_pedido"] for t in respuesta.json()}
    assert ids_pedido == {pedido_propio.id}


def test_cajero_ve_todos_los_tickets(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    token = _token(999, RolNombre.CAJERO)
    respuesta = client.get("/tickets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1


def test_cajero_filtra_pagado_false_solo_ve_cuentas_abiertas(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)
    registrar_venta(db_session, VentaCreate(ticket_id=ticket.id, metodo_pago=MetodoPagoNombre.EFECTIVO, monto=Decimal("100.00")), usuario_id=999)

    token = _token(999, RolNombre.CAJERO)
    respuesta = client.get("/tickets", params={"pagado": "false"}, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json() == []
```

- [ ] **Step 2: Correr el test, verificar que falla**

Run: `cd api && python -m pytest app/tests/test_router_tickets.py -v`
Expected: FAIL con 404 (la ruta `/tickets` no existe todavía)

- [ ] **Step 3: Implementar**

Crear `api/app/routers/tickets.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.pagos import Pago
from app.data.pedidos import Pedido
from app.data.tickets import Ticket
from app.models.ventas import TicketOut
from app.security.auth import TokenData, require_rol

router = APIRouter(prefix="/tickets", tags=["tickets"])

_TICKET_LOAD_OPTIONS = (joinedload(Ticket.pago).joinedload(Pago.metodo),)


@router.get("", response_model=list[TicketOut])
def listar(
    pagado: bool | None = None,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(
        require_rol(RolNombre.MESERO, RolNombre.CAJERO, RolNombre.ADMINISTRADOR)
    ),
) -> list[Ticket]:
    query = db.query(Ticket).options(*_TICKET_LOAD_OPTIONS)

    if usuario.rol == RolNombre.MESERO:
        query = query.join(Pedido, Ticket.id_pedido == Pedido.id).filter(
            Pedido.id_usuario == usuario.user_id
        )

    if pagado is True:
        query = query.join(Pago, Ticket.id == Pago.id_ticket)
    elif pagado is False:
        query = query.outerjoin(Pago, Ticket.id == Pago.id_ticket).filter(Pago.id.is_(None))

    return query.order_by(Ticket.fecha_emision.desc()).all()
```

En `api/app/main.py`, agregar el import junto a los demás routers (orden alfabético como el resto):

```python
from app.routers.tickets import router as tickets_router
```

Y el `include_router` junto a los demás:

```python
app.include_router(tickets_router)
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && python -m pytest app/tests/test_router_tickets.py -v`
Expected: PASS

- [ ] **Step 5: Correr la suite completa del backend**

Run: `cd api && python -m pytest -v`
Expected: PASS (todos)

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/tickets.py api/app/main.py api/app/tests/test_router_tickets.py
git commit -m "feat(api): endpoint GET /tickets con historial filtrado por rol"
```

---

## Mobile

### Task 8: `mobile/api/pedidos.js` — CRUD de items, lista de pedidos por mesa, cerrar cuenta

**Files:**
- Modify: `mobile/api/pedidos.js`
- Modify: `mobile/api/pedidos.test.js`

**Interfaces:**
- Produces: `agregarItemPedido(pedidoId, {idProducto, cantidad, especificaciones})`, `actualizarItemPedido(pedidoId, itemId, {cantidad, especificaciones})`, `eliminarItemPedido(pedidoId, itemId)`, `cerrarCuenta(pedidoId)`, `getPedidosActivosDeMesa(mesaId)` (reemplaza `getPedidoActivoDeMesa`, ahora devuelve una lista). Consumidos por Task 10 y Task 11.

- [ ] **Step 1: Escribir los tests que fallan**

Reemplazar el contenido completo de `mobile/api/pedidos.test.js`:

```javascript
jest.mock('../config', () => ({ API_URL: 'http://test.local' }));
jest.mock('../auth/session', () => ({
  getToken: jest.fn(() => Promise.resolve('fake-token')),
  clearToken: jest.fn(() => Promise.resolve()),
}));

import { getPedidosActivosDeMesa, agregarItemPedido, actualizarItemPedido, eliminarItemPedido, cerrarCuenta } from './pedidos';

function jsonResponse(body) {
  return {
    ok: true,
    status: 200,
    text: () => Promise.resolve(JSON.stringify(body)),
  };
}

const PEDIDO_PENDIENTE = { id: 10, id_mesa: 3, estatus: { nombre: 'Pendiente' } };
const PEDIDO_ENTREGADO = { id: 11, id_mesa: 3, estatus: { nombre: 'Entregado' } };

beforeEach(() => {
  global.fetch = jest.fn((url) => {
    if (url.includes('mesa_id=3')) return Promise.resolve(jsonResponse([PEDIDO_PENDIENTE, PEDIDO_ENTREGADO]));
    if (url.includes('mesa_id=99')) return Promise.resolve(jsonResponse([]));
    return Promise.resolve(jsonResponse({ id: 10 }));
  });
});

afterEach(() => jest.clearAllMocks());

describe('getPedidosActivosDeMesa', () => {
  it('filtra a solo los estados activos (excluye Entregado/Cancelado)', async () => {
    const activos = await getPedidosActivosDeMesa(3);
    expect(activos).toEqual([PEDIDO_PENDIENTE]);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it('devuelve lista vacía cuando la mesa no tiene pedidos', async () => {
    const activos = await getPedidosActivosDeMesa(99);
    expect(activos).toEqual([]);
  });
});

describe('agregarItemPedido', () => {
  it('manda POST a /pedidos/{id}/items con el shape correcto', async () => {
    await agregarItemPedido(10, { idProducto: 5, cantidad: 2, especificaciones: 'Sin azúcar' });
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toContain('/pedidos/10/items');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({ id_producto: 5, cantidad: 2, especificaciones: 'Sin azúcar' });
  });
});

describe('actualizarItemPedido', () => {
  it('manda PUT a /pedidos/{id}/items/{itemId}', async () => {
    await actualizarItemPedido(10, 7, { cantidad: 3 });
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toContain('/pedidos/10/items/7');
    expect(options.method).toBe('PUT');
    expect(JSON.parse(options.body)).toEqual({ cantidad: 3 });
  });
});

describe('eliminarItemPedido', () => {
  it('manda DELETE a /pedidos/{id}/items/{itemId}', async () => {
    await eliminarItemPedido(10, 7);
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toContain('/pedidos/10/items/7');
    expect(options.method).toBe('DELETE');
  });
});

describe('cerrarCuenta', () => {
  it('manda POST a /pedidos/{id}/cerrar-cuenta', async () => {
    await cerrarCuenta(10);
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toContain('/pedidos/10/cerrar-cuenta');
    expect(options.method).toBe('POST');
  });
});
```

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd mobile && npx jest api/pedidos.test.js`
Expected: FAIL — `getPedidosActivosDeMesa` y las demás funciones no existen aún.

- [ ] **Step 3: Implementar**

Reemplazar el contenido completo de `mobile/api/pedidos.js`:

```javascript
import { request } from './client';

// Estados en los que un pedido sigue "vivo" — espejo de
// ESTATUS_PEDIDO_ACTIVOS en api/app/core/constants.py:43-47
const ESTADOS_ACTIVOS = ['Pendiente', 'En preparación', 'Listo'];

export function crearPedido({ mesaId, usuarioId, items }) {
  return request('/pedidos', {
    method: 'POST',
    body: {
      mesa_id: mesaId,
      usuario_id: usuarioId,
      items: items.map((item) => ({
        id_producto: item.id_producto,
        cantidad: item.cantidad,
        especificaciones: item.especificaciones || null,
      })),
    },
  });
}

export function getPedido(pedidoId) {
  return request(`/pedidos/${pedidoId}`);
}

export function cambiarEstadoPedido(pedidoId, estatus) {
  return request(`/pedidos/${pedidoId}/estado`, {
    method: 'PUT',
    body: { estatus },
  });
}

// GET /pedidos?mesa_id= trae TODOS los pedidos de la mesa (cualquier
// estatus); se filtra client-side a los activos para no listar pedidos ya
// Entregados/Cancelados como si siguieran vivos.
export async function getPedidosActivosDeMesa(mesaId) {
  const todos = await request(`/pedidos?mesa_id=${mesaId}&limit=200`);
  return todos.filter((p) => ESTADOS_ACTIVOS.includes(p.estatus.nombre));
}

export function agregarItemPedido(pedidoId, { idProducto, cantidad, especificaciones }) {
  return request(`/pedidos/${pedidoId}/items`, {
    method: 'POST',
    body: { id_producto: idProducto, cantidad, especificaciones: especificaciones || null },
  });
}

export function actualizarItemPedido(pedidoId, itemId, { cantidad, especificaciones }) {
  const body = {};
  if (cantidad !== undefined) body.cantidad = cantidad;
  if (especificaciones !== undefined) body.especificaciones = especificaciones;
  return request(`/pedidos/${pedidoId}/items/${itemId}`, { method: 'PUT', body });
}

export function eliminarItemPedido(pedidoId, itemId) {
  return request(`/pedidos/${pedidoId}/items/${itemId}`, { method: 'DELETE' });
}

export function cerrarCuenta(pedidoId) {
  return request(`/pedidos/${pedidoId}/cerrar-cuenta`, { method: 'POST' });
}
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd mobile && npx jest api/pedidos.test.js`
Expected: PASS

- [ ] **Step 5: Buscar y confirmar que no queda ninguna referencia a `getPedidoActivoDeMesa`**

Run: `cd mobile && grep -rn "getPedidoActivoDeMesa" --include="*.js" .`
Expected: sin resultados (Task 11 reemplaza su único caller en `MesasScreen.js`; si esta búsqueda se corre antes de Task 11, es esperable encontrar ese caller todavía — no bloquea este Task, se resuelve en Task 11).

- [ ] **Step 6: Commit**

```bash
git add mobile/api/pedidos.js mobile/api/pedidos.test.js
git commit -m "feat(mobile): CRUD de items de pedido, lista de pedidos por mesa, cerrar cuenta"
```

---

### Task 9: `mobile/api/caja.js` (ticket_id) + `mobile/api/tickets.js` nuevo

**Files:**
- Modify: `mobile/api/caja.js`
- Create: `mobile/api/tickets.js`
- Create: `mobile/api/tickets.test.js`

**Interfaces:**
- Produces: `registrarVenta({ticketId, metodoPago, monto})` (firma cambiada), `getTickets({pagado} = {})` en el nuevo `tickets.js`. Consumidos por Task 12 y Task 13.

- [ ] **Step 1: Escribir el test que falla (archivo nuevo)**

```javascript
// mobile/api/tickets.test.js
jest.mock('../config', () => ({ API_URL: 'http://test.local' }));
jest.mock('../auth/session', () => ({
  getToken: jest.fn(() => Promise.resolve('fake-token')),
  clearToken: jest.fn(() => Promise.resolve()),
}));

import { getTickets } from './tickets';

function jsonResponse(body) {
  return { ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(body)) };
}

beforeEach(() => {
  global.fetch = jest.fn(() => Promise.resolve(jsonResponse([])));
});

afterEach(() => jest.clearAllMocks());

describe('getTickets', () => {
  it('sin filtro pide /tickets sin query', async () => {
    await getTickets();
    expect(global.fetch.mock.calls[0][0]).toContain('/tickets');
    expect(global.fetch.mock.calls[0][0]).not.toContain('?');
  });

  it('con pagado:false agrega el query param', async () => {
    await getTickets({ pagado: false });
    expect(global.fetch.mock.calls[0][0]).toContain('/tickets?pagado=false');
  });
});
```

- [ ] **Step 2: Correr el test, verificar que falla**

Run: `cd mobile && npx jest api/tickets.test.js`
Expected: FAIL — `mobile/api/tickets.js` no existe.

- [ ] **Step 3: Implementar**

Crear `mobile/api/tickets.js`:

```javascript
import { request } from './client';

export function getTickets({ pagado } = {}) {
  const query = pagado === undefined ? '' : `?pagado=${pagado}`;
  return request(`/tickets${query}`);
}
```

Modificar `mobile/api/caja.js`:

```javascript
import { request } from './client';

export function registrarVenta({ ticketId, metodoPago, monto }) {
  return request('/ventas', {
    method: 'POST',
    body: { ticket_id: ticketId, metodo_pago: metodoPago, monto },
  });
}

export function getResumenCaja(desde, hasta) {
  const params = new URLSearchParams();
  if (desde) params.append('desde', desde);
  if (hasta) params.append('hasta', hasta);
  const query = params.toString();
  return request(`/caja/resumen${query ? `?${query}` : ''}`);
}
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd mobile && npx jest api/tickets.test.js`
Expected: PASS

- [ ] **Step 5: Confirmar que no queda ningún caller de `registrarVenta` con el shape viejo**

Run: `cd mobile && grep -rn "registrarVenta(" --include="*.js" .`
Expected: el único caller es `PagoScreen.js` — se actualiza en Task 13. Si este Task se ejecuta antes, es esperable que `PagoScreen.js` quede temporalmente rota (llama con `pedidoId` en vez de `ticketId`); no bloquea este Task, Task 13 lo corrige.

- [ ] **Step 6: Commit**

```bash
git add mobile/api/caja.js mobile/api/tickets.js mobile/api/tickets.test.js
git commit -m "feat(mobile): registrarVenta usa ticket_id, nuevo cliente GET /tickets"
```

---

### Task 10: `DetalleScreen.js` — edición de items en Pendiente + botón Cerrar cuenta

**Files:**
- Modify: `mobile/screens/DetalleScreen.js`

**Interfaces:**
- Consumes: `agregarItemPedido`, `actualizarItemPedido`, `eliminarItemPedido`, `cerrarCuenta`, `getPedido`, `cambiarEstadoPedido` de `mobile/api/pedidos.js` (Task 8). `getProductos` de `mobile/api/productos.js` (ya existente, mismo patrón que `PedidoScreen.js`).

- [ ] **Step 1: Implementar**

Reemplazar el contenido completo de `mobile/screens/DetalleScreen.js`:

```javascript
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ScrollView, FlatList } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import {
  getPedido,
  cambiarEstadoPedido,
  agregarItemPedido,
  actualizarItemPedido,
  eliminarItemPedido,
  cerrarCuenta,
} from '../api/pedidos';
import { getProductos } from '../api/productos';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { connectToChannel } from '../ws/client';
import { Card } from '../components/Card';
import { ListItem } from '../components/ListItem';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { colors, typography, spacing } from '../theme';
import { TONE_POR_ESTATUS_PEDIDO } from '../constants/estatusPedido';

export default function DetalleScreen({ route, navigation }) {
  const { pedidoId, numeroMesa } = route.params;
  const { rol } = useAuth();
  const [pedido, setPedido] = useState(null);
  const [menu, setMenu] = useState([]);
  const [loading, setLoading] = useState(true);
  const [entregando, setEntregando] = useState(false);
  const [cerrandoCuenta, setCerrandoCuenta] = useState(false);
  const [editandoItemId, setEditandoItemId] = useState(null);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getPedido(pedidoId);
      setPedido(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar el pedido');
    } finally {
      setLoading(false);
    }
  }, [pedidoId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  useFocusEffect(
    useCallback(() => {
      let cancelado = false;
      (async () => {
        try {
          const productos = await getProductos();
          if (!cancelado) setMenu(productos.filter((p) => p.disponible !== false));
        } catch (err) {
          // el menú es solo para agregar items; si falla, se oculta esa sección
        }
      })();
      return () => {
        cancelado = true;
      };
    }, [])
  );

  useFocusEffect(
    useCallback(() => {
      let cerrar = null;
      let cancelado = false;

      connectToChannel('mesero', {
        onMessage: (evento) => {
          if (evento.evento === 'pedido_listo' && evento.pedido_id === pedidoId) {
            cargar();
          }
        },
        onClose: cargar,
      }).then((unsub) => {
        if (cancelado) {
          unsub();
          return;
        }
        cerrar = unsub;
      });

      return () => {
        cancelado = true;
        if (cerrar) cerrar();
      };
    }, [pedidoId, cargar])
  );

  const marcarEntregado = async () => {
    setEntregando(true);
    setError('');
    try {
      setPedido(await cambiarEstadoPedido(pedidoId, 'Entregado'));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo marcar como entregado');
    } finally {
      setEntregando(false);
    }
  };

  const handleCerrarCuenta = async () => {
    setCerrandoCuenta(true);
    setError('');
    try {
      await cerrarCuenta(pedidoId);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cerrar la cuenta');
    } finally {
      setCerrandoCuenta(false);
    }
  };

  const cambiarCantidad = async (itemId, nuevaCantidad) => {
    if (nuevaCantidad < 1) return;
    setEditandoItemId(itemId);
    setError('');
    try {
      setPedido(await actualizarItemPedido(pedidoId, itemId, { cantidad: nuevaCantidad }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo actualizar el ítem');
    } finally {
      setEditandoItemId(null);
    }
  };

  const quitarItem = async (itemId) => {
    setEditandoItemId(itemId);
    setError('');
    try {
      setPedido(await eliminarItemPedido(pedidoId, itemId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo quitar el ítem');
    } finally {
      setEditandoItemId(null);
    }
  };

  const agregarProducto = async (producto) => {
    setError('');
    try {
      setPedido(await agregarItemPedido(pedidoId, { idProducto: producto.id, cantidad: 1 }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo agregar el producto');
    }
  };

  if (loading && !pedido) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (error && !pedido) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error}</Text>
        <Button variant="primary" label="Reintentar" onPress={cargar} />
      </View>
    );
  }

  const esMeseroOAdmin = rol === 'Mesero' || rol === 'Administrador';
  const esPendiente = pedido.estatus.nombre === 'Pendiente';
  const esListo = pedido.estatus.nombre === 'Listo';
  const puedeEditar = esMeseroOAdmin && esPendiente;
  const puedeCerrarCuenta = esMeseroOAdmin && esListo;
  const puedeEntregar = esMeseroOAdmin && esListo;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      <Card style={styles.infoCard}>
        <Text style={styles.title}>Pedido #{pedido.id} — Mesa {numeroMesa ?? pedido.id_mesa}</Text>
        <Badge
          label={pedido.estatus.nombre}
          tone={TONE_POR_ESTATUS_PEDIDO[pedido.estatus.nombre] || 'neutral'}
        />
      </Card>

      {pedido.detalle.map((item) => (
        <ListItem
          key={item.id}
          title={`${item.producto.nombre} x${item.cantidad}`}
          subtitle={`$${item.precio_unitario} c/u`}
          trailing={
            puedeEditar ? (
              <View style={styles.editRow}>
                <Button
                  variant="text"
                  label="-"
                  onPress={() => cambiarCantidad(item.id, item.cantidad - 1)}
                  disabled={editandoItemId === item.id}
                />
                <Button
                  variant="text"
                  label="+"
                  onPress={() => cambiarCantidad(item.id, item.cantidad + 1)}
                  disabled={editandoItemId === item.id}
                />
                <Button
                  variant="text"
                  label="Quitar"
                  onPress={() => quitarItem(item.id)}
                  disabled={editandoItemId === item.id}
                />
              </View>
            ) : (
              <Badge label={item.estatus.nombre} tone="neutral" />
            )
          }
        />
      ))}

      {puedeEditar && (
        <>
          <Text style={styles.subtitle}>Agregar producto</Text>
          <FlatList
            data={menu}
            keyExtractor={(item) => item.id.toString()}
            renderItem={({ item }) => (
              <ListItem
                title={item.nombre}
                subtitle={`$${item.precio_venta}`}
                trailing={<Text style={styles.agregar}>+</Text>}
                onPress={() => agregarProducto(item)}
              />
            )}
          />
        </>
      )}

      {pedido.total !== null && (
        <Text style={styles.total}>Total: ${pedido.total}</Text>
      )}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {puedeCerrarCuenta && (
        <View style={styles.entregarWrap}>
          <Button
            variant="secondary"
            label={cerrandoCuenta ? 'Cerrando...' : 'Cerrar cuenta'}
            onPress={handleCerrarCuenta}
            disabled={cerrandoCuenta}
          />
        </View>
      )}

      {puedeEntregar && (
        <View style={styles.entregarWrap}>
          <Button
            variant="primary"
            label={entregando ? 'Actualizando...' : 'Marcar como Entregado'}
            onPress={marcarEntregado}
            disabled={entregando}
          />
        </View>
      )}

      <Button variant="text" label="Actualizar" onPress={cargar} />

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.xl },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.xl, gap: spacing.lg },
  infoCard: { marginBottom: spacing.lg, gap: spacing.sm },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
  },
  subtitle: {
    marginTop: spacing.lg,
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  error: { color: colors.danger, marginBottom: spacing.lg, textAlign: 'center' },
  total: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginTop: spacing.md,
    marginBottom: spacing.xl,
  },
  entregarWrap: { marginBottom: spacing.sm },
  editRow: { flexDirection: 'row', gap: spacing.sm },
  agregar: { fontWeight: typography.weight.bold, color: colors.primary, fontSize: typography.size.xl },
});
```

Nota de diseño: `puedeEntregar` ya no necesita cambiar (sigue siendo "Listo" + rol), el gate real vive en el backend (Task 5) — si el Mesero no cerró cuenta y toca "Marcar como Entregado", el backend devuelve 409 con el mensaje "No se puede entregar un pedido sin cobrar" y `marcarEntregado` ya lo captura en el bloque `catch` existente, mostrándolo en `error`. No hace falta ocultar el botón condicionalmente a que exista Ticket — sería una llamada extra a `GET /tickets` solo para decidir visibilidad; el mensaje de error del backend ya comunica el motivo.

- [ ] **Step 2: Verificación manual contra Docker**

No hay test automatizado de componente para pantallas en este proyecto (ver precedente en `.superpowers/sdd/progress.md`, sesión 2026-08-07: "component testing desproporcionado por ahora"). Verificar manualmente:

1. Levantar `docker compose up` (API en el puerto configurado) y `npx expo start` en `mobile/`.
2. Login como Mesero, crear un pedido nuevo (queda Pendiente).
3. Abrir `DetalleScreen` de ese pedido: confirmar que aparecen los controles +/-/Quitar en cada item y la sección "Agregar producto".
4. Agregar un producto nuevo, confirmar que aparece en la lista y el total (si ya tiene items previos) se recalcula al recargar.
5. Bajar la cantidad de un item a 0 vía "-" repetido hasta 1 y luego "Quitar" en el último item restante: confirmar que el backend devuelve el error "El pedido debe tener al menos un ítem" y se muestra en pantalla.
6. Como Cocinero, avanzar el pedido a "En preparación": volver a `DetalleScreen` como Mesero, confirmar que los controles de edición desaparecen (vuelve a modo solo-lectura).
7. Avanzar el pedido a "Listo" (vía `ColaPedidosScreen`): confirmar que aparece el botón "Cerrar cuenta" junto a "Marcar como Entregado".
8. Tocar "Marcar como Entregado" sin haber cerrado cuenta: confirmar que se muestra el error del backend, el pedido NO pasa a Entregado.
9. Tocar "Cerrar cuenta": confirmar que no truena, recarga el pedido (sigue en Listo). Tocar "Marcar como Entregado" de nuevo: sigue fallando porque falta el Pago (esperado hasta Task 13, donde Cajero paga) — confirmar que el mensaje de error sigue siendo claro.

- [ ] **Step 3: Commit**

```bash
git add mobile/screens/DetalleScreen.js
git commit -m "feat(mobile): edicion de items en Pendiente y boton Cerrar cuenta en DetalleScreen"
```

---

### Task 11: `MesasScreen.js` + `PedidosMesaScreen.js` — multi-pedido por mesa

**Files:**
- Modify: `mobile/screens/MesasScreen.js`
- Create: `mobile/screens/PedidosMesaScreen.js`
- Modify: `mobile/App.js` (registrar la ruta nueva)

**Interfaces:**
- Consumes: `getPedidosActivosDeMesa(mesaId)` de Task 8.
- Produces: ruta `PedidosMesa` — navega ahí cualquier toque a una mesa Ocupada.

- [ ] **Step 1: Implementar `MesasScreen.js`**

Reemplazar la función `abrirMesa` y el import de `pedidos` en `mobile/screens/MesasScreen.js`:

```javascript
import { getMesas } from '../api/mesas';
```

(se elimina el import de `getPedidoActivoDeMesa` de `../api/pedidos` — ya no se usa en esta pantalla)

```javascript
  const abrirMesa = (mesa) => {
    if (mesa.estatus.nombre !== 'Ocupada') {
      navigation.navigate('Pedido', { mesaId: mesa.id, numeroMesa: mesa.numero_mesa });
      return;
    }
    navigation.navigate('PedidosMesa', { mesaId: mesa.id, numeroMesa: mesa.numero_mesa });
  };
```

Esto reemplaza toda la función `abrirMesa` original (líneas 42-66 del archivo leído en el brainstorm), incluyendo el estado `abriendo`/`setAbriendo` que ya no hace falta — quitar también `const [abriendo, setAbriendo] = useState(null);` y las referencias a `abriendo`/`setAbriendo` en el render (`item.id === abriendo ? styles.cardDisabled : null` → `null`; el texto `{abriendo === item.id ? ... }` se elimina).

El archivo completo queda:

```javascript
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getMesas } from '../api/mesas';
import { ApiError } from '../api/client';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { colors, typography, spacing } from '../theme';

const TONE_POR_ESTATUS = {
  Libre: 'success',
  Ocupada: 'danger',
  Reservada: 'warning',
};

export default function MesasScreen({ navigation }) {
  const [mesas, setMesas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargarMesas = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getMesas();
      setMesas(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargarMesas();
    }, [cargarMesas])
  );

  const abrirMesa = (mesa) => {
    if (mesa.estatus.nombre !== 'Ocupada') {
      navigation.navigate('Pedido', { mesaId: mesa.id, numeroMesa: mesa.numero_mesa });
      return;
    }
    navigation.navigate('PedidosMesa', { mesaId: mesa.id, numeroMesa: mesa.numero_mesa });
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Mesas</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={mesas}
        keyExtractor={(item) => item.id.toString()}
        numColumns={2}
        renderItem={({ item }) => (
          <View style={styles.cardWrap}>
            <Card onPress={() => abrirMesa(item)}>
              <Text style={styles.mesaNumero}>Mesa {item.numero_mesa}</Text>
              <Badge label={item.estatus.nombre} tone={TONE_POR_ESTATUS[item.estatus.nombre] || 'neutral'} />
              <Text style={styles.capacidad}>Capacidad: {item.capacidad}</Text>
            </Card>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
    textAlign: 'center',
  },
  error: { color: colors.danger, textAlign: 'center', marginBottom: spacing.md },
  cardWrap: { flex: 1, margin: spacing.xs },
  mesaNumero: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  capacidad: { color: colors.textSecondary, marginTop: spacing.sm, fontSize: typography.size.md },
});
```

- [ ] **Step 2: Crear `PedidosMesaScreen.js`**

```javascript
// mobile/screens/PedidosMesaScreen.js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedidosActivosDeMesa } from '../api/pedidos';
import { ApiError } from '../api/client';
import { Card } from '../components/Card';
import { ListItem } from '../components/ListItem';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';
import { TONE_POR_ESTATUS_PEDIDO } from '../constants/estatusPedido';

export default function PedidosMesaScreen({ route, navigation }) {
  const { mesaId, numeroMesa } = route.params;
  const [pedidos, setPedidos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPedidos(await getPedidosActivosDeMesa(mesaId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, [mesaId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Mesa {numeroMesa}</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={pedidos}
        keyExtractor={(item) => item.id.toString()}
        ListEmptyComponent={
          <EmptyState icon="receipt-outline" message="Sin pedidos activos en esta mesa." />
        }
        renderItem={({ item }) => (
          <ListItem
            title={`Pedido #${item.id}`}
            subtitle={`${item.detalle.length} ítem(s)`}
            trailing={
              <Badge
                label={item.estatus.nombre}
                tone={TONE_POR_ESTATUS_PEDIDO[item.estatus.nombre] || 'neutral'}
              />
            }
            onPress={() => navigation.navigate('Detalle', { pedidoId: item.id, numeroMesa })}
          />
        )}
      />

      <Button
        variant="primary"
        label="Nuevo pedido"
        onPress={() => navigation.navigate('Pedido', { mesaId, numeroMesa })}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
    textAlign: 'center',
  },
  error: { color: colors.danger, textAlign: 'center', marginBottom: spacing.md },
});
```

- [ ] **Step 3: Registrar la ruta en `App.js`**

Agregar el import junto a los demás screens:

```javascript
import PedidosMesaScreen from './screens/PedidosMesaScreen';
```

Y el `Stack.Screen`, junto al de `Detalle`:

```javascript
        <Stack.Screen
          name="PedidosMesa"
          component={PedidosMesaScreen}
        />
```

- [ ] **Step 4: Verificación manual contra Docker**

1. Con una mesa Libre, tocarla: confirma que sigue yendo directo a `PedidoScreen` (comportamiento sin cambios).
2. Crear un pedido en una mesa (queda Ocupada). Volver a Mesas, tocar esa mesa: confirmar que ahora navega a `PedidosMesaScreen` y lista ese pedido.
3. Desde `PedidosMesaScreen`, tocar "Nuevo pedido": confirmar que crea un segundo pedido en la misma mesa sin error (antes esto era imposible).
4. Volver a `PedidosMesaScreen`: confirmar que ahora lista los 2 pedidos activos.
5. Marcar uno de los dos pedidos como Entregado (cerrando cuenta + pagando primero, ver Task 13): confirmar que `PedidosMesaScreen` ya no lo lista (solo activos) y que la mesa sigue Ocupada mientras el otro pedido siga activo.

- [ ] **Step 5: Commit**

```bash
git add mobile/screens/MesasScreen.js mobile/screens/PedidosMesaScreen.js mobile/App.js
git commit -m "feat(mobile): soporte real de multiples pedidos concurrentes por mesa"
```

---

### Task 12: `CajaScreen.js` — cola de cuentas cerradas en vez de pedidos Listo

**Files:**
- Modify: `mobile/api/pedidos_caja.js`
- Modify: `mobile/screens/CajaScreen.js`

**Interfaces:**
- Consumes: `getTickets({pagado: false})` de Task 9.

- [ ] **Step 1: Implementar `pedidos_caja.js`**

Reemplazar `mobile/api/pedidos_caja.js` completo:

```javascript
import { request } from './client';

export function getPedido(pedidoId) {
  return request(`/pedidos/${pedidoId}`);
}
```

(se elimina `getPedidosListos` — `CajaScreen.js` pasa a usar `getTickets` de `api/tickets.js`)

- [ ] **Step 2: Implementar `CajaScreen.js`**

Reemplazar el contenido completo de `mobile/screens/CajaScreen.js`:

```javascript
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getTickets } from '../api/tickets';
import { getMesas } from '../api/mesas';
import { ApiError } from '../api/client';
import { connectToChannel } from '../ws/client';
import { Button } from '../components/Button';
import { ListItem } from '../components/ListItem';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

export default function CajaScreen({ navigation }) {
  const [tickets, setTickets] = useState([]);
  const [numeroPorMesa, setNumeroPorMesa] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [lista, mesas] = await Promise.all([getTickets({ pagado: false }), getMesas()]);
      setTickets(lista);
      setNumeroPorMesa(Object.fromEntries(mesas.map((m) => [m.id, m.numero_mesa])));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  useFocusEffect(
    useCallback(() => {
      let cerrar = null;
      let cancelado = false;

      connectToChannel('caja', {
        onMessage: (evento) => {
          if (evento.evento === 'pedido_activado') {
            cargar();
          }
        },
        onClose: cargar,
      }).then((unsub) => {
        if (cancelado) {
          unsub();
          return;
        }
        cerrar = unsub;
      });

      return () => {
        cancelado = true;
        if (cerrar) cerrar();
      };
    }, [cargar])
  );

  if (loading && tickets.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Caja</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={tickets}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingBottom: spacing.xxl }}
        ListEmptyComponent={
          <EmptyState
            icon="cash-outline"
            message="Sin cuentas por cobrar. Aparecerán aquí cuando el Mesero cierre la cuenta de un pedido Listo."
          />
        }
        renderItem={({ item }) => (
          <ListItem
            title={`Mesa ${numeroPorMesa[item.id_pedido] ?? item.id_pedido}`}
            subtitle={`Ticket #${item.id} — Total $${item.total}`}
            trailing={
              <Button
                variant="primary"
                label="Cobrar"
                onPress={() =>
                  navigation.navigate('Pago', {
                    ticketId: item.id,
                    numeroMesa: numeroPorMesa[item.id_pedido],
                  })
                }
              />
            }
          />
        )}
        ListFooterComponent={() => (
          <View>
            <Button
              variant="secondary"
              label="Gastos y cuentas"
              onPress={() => navigation.navigate('Gastos')}
            />
          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  error: { color: colors.danger, marginBottom: spacing.md },
});
```

Nota real: `TicketOut` no trae `id_mesa` directo (solo `id_pedido`) — el mapeo `numeroPorMesa[item.id_pedido]` de arriba está MAL, `numeroPorMesa` está indexado por `id_mesa`, no por `id_pedido`. `GET /tickets` no devuelve la mesa del pedido. Antes de usar este código, resolver esto en el Step 2.1 siguiente (no dejarlo como bug conocido).

- [ ] **Step 2.1: Corregir el gap real de datos — `TicketOut` no expone la mesa**

`CajaScreen` necesita mostrar "Mesa N" por cada ticket pendiente de cobro, pero `GET /tickets` solo devuelve `id_pedido`, no la mesa asociada. Opción más barata: pedir también `GET /pedidos?mesa_id=` no aplica aquí (no se conoce la mesa de antemano); en cambio, cargar los pedidos de los tickets vía `GET /pedidos/{id}` en paralelo es una llamada N+1. La opción correcta y barata es agregar `id_mesa` a `TicketOut` en el backend — volver a Task 4 y ajustar el modelo:

En `api/app/models/ventas.py`, la clase `TicketOut` agrega el campo (esto es un ajuste retroactivo a Task 4, hacerlo ahora si Task 4 ya se ejecutó, o incluirlo directo si se está ejecutando este plan en orden):

```python
class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subtotal: Decimal
    iva: Decimal
    total: Decimal
    fecha_emision: datetime
    id_pedido: int
    id_mesa: int
    id_usuario: int
    pago: PagoOut | None = None
```

`Ticket` no tiene `id_mesa` propio (vive en `Pedido`), así que el ORM no lo resuelve automáticamente vía `from_attributes` con un simple atributo — hace falta un campo calculado. Cambiar a un `@computed_field` o resolverlo en el router. Más simple: resolverlo en el router de `tickets.py` (Task 7) con `joinedload(Ticket.pedido)` y construir la respuesta manualmente en vez de dejar que `response_model` infiera todo:

En `api/app/routers/tickets.py` (Task 7), agregar `joinedload(Ticket.pedido)` a `_TICKET_LOAD_OPTIONS`:

```python
_TICKET_LOAD_OPTIONS = (
    joinedload(Ticket.pago).joinedload(Pago.metodo),
    joinedload(Ticket.pedido),
)
```

Y en el endpoint `crear_venta` de `api/app/routers/caja.py` (Task 6 lo toca, agregar ahí también el mismo `joinedload`) y en `cerrar_cuenta_endpoint` de `api/app/routers/pedidos.py` (Task 4), asegurar que el objeto `Ticket` devuelto tenga `pedido` cargado — FastAPI con `response_model=TicketOut` y `from_attributes=True` accede a `ticket.id_mesa`, que no existe como columna. La forma correcta: agregar una property a nivel Python en el modelo ORM `Ticket` (`api/app/data/tickets.py`), no en el schema:

```python
# api/app/data/tickets.py — agregar al final de la clase Ticket
    @property
    def id_mesa(self) -> int:
        return self.pedido.id_mesa
```

Con esto, `TicketOut.model_validate(ticket)` (que Pydantic hace automático vía `response_model` + `from_attributes=True`) resuelve `id_mesa` como cualquier otro atributo, siempre que `ticket.pedido` esté cargado (por eso el `joinedload(Ticket.pedido)` en cada endpoint que devuelve `TicketOut`: `routers/tickets.py`, `routers/caja.py::crear_venta`, `routers/pedidos.py::cerrar_cuenta_endpoint`).

Revisar `routers/caja.py::crear_venta` (ya existente desde antes de este plan) y confirmar que su query también tenga el `joinedload(Ticket.pedido)`:

```python
@router.post("/ventas", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def crear_venta(
    datos: VentaCreate,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(_requiere_caja),
) -> Ticket:
    ticket = registrar_venta(db, datos, usuario_id=usuario.user_id)
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.pago).joinedload(Pago.metodo), joinedload(Ticket.pedido))
        .filter(Ticket.id == ticket.id)
        .first()
    )
```

Y en `routers/pedidos.py::cerrar_cuenta_endpoint`, cargar el pedido explícitamente antes de devolver (el `pedido` que ya se tiene en la función viene de `_get_pedido_o_404`, que sí carga todo — pero el `Ticket` devuelto por `cerrar_cuenta(db, pedido, ...)` no trae `pedido` precargado en su propia relación ORM a menos que SQLAlchemy la resuelva lazy; como la sesión sigue abierta, el lazy-load funciona sin problema, no hace falta cambiar nada ahí — confirmarlo corriendo el test de Task 4 con `assert ticket.id_mesa == pedido.id_mesa` agregado).

Agregar ese assert a `test_cerrar_cuenta_calcula_totales_y_no_crea_pago` en `api/app/tests/test_services_tickets.py`:

```python
    assert ticket.id_mesa == mesa_libre.id
```

Con `CajaScreen.js`, corregir la línea de `title`:

```javascript
            title={`Mesa ${numeroPorMesa[item.id_mesa] ?? item.id_mesa}`}
```

- [ ] **Step 3: Correr la suite completa del backend (confirma que el ajuste retroactivo no rompe nada)**

Run: `cd api && python -m pytest -v`
Expected: PASS (todos)

- [ ] **Step 4: Verificación manual contra Docker**

1. Cerrar la cuenta de un pedido Listo (Mesero, ver Task 10). Ir a `CajaScreen` como Cajero: confirmar que aparece con "Mesa N" correcto y el total del ticket.
2. Confirmar que un pedido Listo SIN cuenta cerrada NO aparece en esta cola (a diferencia del comportamiento viejo).

- [ ] **Step 5: Commit**

```bash
git add api/app/models/ventas.py api/app/data/tickets.py api/app/routers/tickets.py api/app/routers/caja.py api/app/tests/test_services_tickets.py mobile/api/pedidos_caja.js mobile/screens/CajaScreen.js
git commit -m "feat: CajaScreen consume cola de cuentas cerradas via GET /tickets, TicketOut expone id_mesa"
```

---

### Task 13: `PagoScreen.js` — recibe `ticketId` en vez de `pedidoId`

**Files:**
- Modify: `mobile/screens/PagoScreen.js`

**Interfaces:**
- Consumes: `registrarVenta({ticketId, metodoPago, monto})` de Task 9, `GET /tickets` no expone un "get by id" — se resuelve trayendo la lista y filtrando, ver Step 1.

- [ ] **Step 1: Implementar**

`PagoScreen` hoy carga el pedido vía `getPedido(pedidoId)` (de `api/pedidos_caja.js`) para mostrar items y calcular el subtotal estimado client-side. Con el nuevo flujo, el `Ticket` YA tiene `subtotal`/`iva`/`total` calculados por `cerrar_cuenta` — no hace falta recalcular nada client-side, y no hace falta cargar el pedido para mostrar sus items tampoco... salvo que si se quiere seguir mostrando el detalle de items, sigue haciendo falta `GET /pedidos/{id}`. La navegación desde `CajaScreen` (Task 12) manda `ticketId`, no `pedidoId` — pero el pedido asociado se puede pedir vía `GET /pedidos/{id}` si se manda también `pedidoId` en la navegación. Ajuste: `CajaScreen.js` (Task 12) ya navega con `{ ticketId: item.id, numeroMesa }` — agregar también `pedidoId: item.id_pedido` a esa navegación (volver a Task 12, `CajaScreen.js`, línea de `navigation.navigate('Pago', {...})`):

```javascript
                onPress={() =>
                  navigation.navigate('Pago', {
                    ticketId: item.id,
                    pedidoId: item.id_pedido,
                    numeroMesa: numeroPorMesa[item.id_mesa],
                  })
                }
```

Reemplazar el contenido completo de `mobile/screens/PagoScreen.js`:

```javascript
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido } from '../api/pedidos_caja';
import { registrarVenta } from '../api/caja';
import { ApiError } from '../api/client';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Chip } from '../components/Chip';
import { Input } from '../components/Input';
import { colors, typography, spacing, radii } from '../theme';

const METODOS = [
  { key: 'Efectivo', label: 'Efectivo' },
  { key: 'Tarjeta débito', label: 'Tarjeta débito' },
  { key: 'Tarjeta crédito', label: 'Tarjeta crédito' },
  { key: 'Transferencia', label: 'Transferencia' },
];

export default function PagoScreen({ route, navigation }) {
  const { ticketId, pedidoId, numeroMesa } = route.params;

  const [pedido, setPedido] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metodoPago, setMetodoPago] = useState('');
  const [monto, setMonto] = useState('');
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState(null);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPedido(await getPedido(pedidoId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar el pedido');
    } finally {
      setLoading(false);
    }
  }, [pedidoId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const pagar = async () => {
    if (!metodoPago) {
      setError('Selecciona un método de pago');
      return;
    }
    if (!monto || Number(monto) <= 0) {
      setError('Ingresa el monto recibido');
      return;
    }

    setProcesando(true);
    setError('');
    try {
      const ticket = await registrarVenta({ ticketId, metodoPago, monto: Number(monto) });
      setResultado(ticket);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo procesar el pago');
    } finally {
      setProcesando(false);
    }
  };

  if (loading && !pedido) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (error && !pedido) {
    return (
      <View style={styles.center}>
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
        <Button variant="primary" label="Reintentar" onPress={cargar} />
      </View>
    );
  }

  if (resultado) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>Pago registrado</Text>
        <Text style={styles.text}>Total: ${resultado.total}</Text>
        <Text style={styles.text}>Cambio: ${resultado.pago.cambio}</Text>
        <Button variant="primary" label="Volver a Caja" onPress={() => navigation.navigate('Caja')} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: spacing.xxl }}>

      <Text style={styles.title}>Procesar Pago</Text>

      <Card>
        <Text style={styles.subtitle}>Mesa {numeroMesa ?? pedido.id_mesa} — Pedido #{pedido.id}</Text>

        {pedido.detalle.map((item) => (
          <Text key={item.id} style={styles.text}>
            {item.producto.nombre} x{item.cantidad} — ${item.precio_unitario}
          </Text>
        ))}
      </Card>

      <Text style={styles.subtitle}>Método de pago</Text>

      <View style={styles.row}>
        {METODOS.map((m) => (
          <Chip
            key={m.key}
            label={m.label}
            selected={metodoPago === m.key}
            onPress={() => !procesando && setMetodoPago(m.key)}
          />
        ))}
      </View>

      <Input
        label="Monto recibido"
        keyboardType="numeric"
        placeholder="Ej. 200"
        value={monto}
        onChangeText={setMonto}
        editable={!procesando}
      />

      {error ? (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <Button
        variant="primary"
        label="Confirmar y Pagar"
        onPress={pagar}
        loading={procesando}
        disabled={procesando}
      />

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.xl },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  subtitle: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  text: { fontSize: typography.size.lg, color: colors.textPrimary },
  errorBanner: {
    backgroundColor: colors.dangerTint,
    borderWidth: 1,
    borderColor: 'rgba(192,57,43,0.3)',
    borderRadius: radii.r8,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  errorText: { color: colors.danger, fontSize: typography.size.md },
  row: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing.md },
});
```

Nota: se quitó el bloque "Subtotal (sin IVA)" y el hint "El total final con IVA lo calcula el servidor al confirmar" — ese cálculo estimado client-side (hallazgo #9, explícitamente fuera de alcance de este plan) dependía de `pedido.detalle` y no tenía forma limpia de mostrarse ahora que el total real ya vive en el `Ticket` (no se está pasando el `Ticket` completo a esta pantalla, solo `ticketId`). Si se quiere seguir mostrando un total antes de cobrar, la superficie más barata es un `GET /tickets` filtrado por id — no existe ese endpoint singular todavía. Se deja fuera de este plan (consistente con el spec, #9 sigue fuera de alcance) y se documenta esta pérdida de funcionalidad menor explícitamente aquí para que no se lea como un descuido silencioso.

- [ ] **Step 2: Actualizar `CajaScreen.js` con el `pedidoId` extra en la navegación (ver arriba)**

Aplicar el cambio de navegación mostrado en el Step 1 sobre el archivo ya escrito en Task 12.

- [ ] **Step 3: Verificación manual contra Docker — flujo completo end-to-end**

1. Mesero crea pedido, cocina lo avanza a Listo, Mesero cierra cuenta (Task 10).
2. Cajero ve la cuenta en `CajaScreen` (Task 12), toca "Cobrar".
3. `PagoScreen` carga bien el detalle del pedido, Cajero paga con monto suficiente: confirmar pantalla de "Pago registrado" con total/cambio correctos.
4. Cajero paga con monto insuficiente: confirmar que el 400 del backend se muestra bien.
5. Volver como Mesero a `DetalleScreen` del mismo pedido: tocar "Marcar como Entregado": confirmar que esta vez SÍ funciona (Ticket ya tiene Pago) y la mesa se libera si no hay más pedidos activos.
6. Confirmar en `GET /tickets?pagado=false` (via curl o Postman) que ese ticket ya no aparece tras pagarlo.

- [ ] **Step 4: Commit**

```bash
git add mobile/screens/PagoScreen.js mobile/screens/CajaScreen.js
git commit -m "feat(mobile): PagoScreen cobra contra un ticket cerrado en vez de un pedido directo"
```

---

## Self-Review

**Spec coverage:**
- #2 (editar pedido Pendiente) → Tasks 2, 3, 8, 10. ✓
- #3 (multi-pedido por mesa) → Tasks 1, 8, 11. ✓
- #4 (cerrar cuenta + gate de pago) → Tasks 4, 5, 6, 8, 10, 12, 13. ✓
- #11c (base de historial de tickets) → Task 7, 9. UI de recibo (#11a/b) queda fuera, como marca el spec. ✓
- Nota de implementación del spec sobre `estado` múltiple en `GET /pedidos` → resuelta en Task 8 con `mesa_id` sin filtro de estado (1 sola llamada, filtro de activos client-side) — más barato que 3 llamadas, decisión tomada explícitamente ahí.

**Placeholder scan:** sin TBD/TODO. El Task 12 Step 2.1 documenta un gap real encontrado a mitad de la escritura del plan (`TicketOut` sin `id_mesa`) con la solución completa in-line, no como nota pendiente.

**Type consistency:** `ticketId`/`ticket_id` consistente entre Task 6 (backend `VentaCreate.ticket_id`), Task 9 (`registrarVenta({ticketId})`), Task 12/13 (navegación `ticketId`). `cerrarCuenta(pedidoId)` consistente entre Task 8 y su uso en Task 10. `getPedidosActivosDeMesa(mesaId)` consistente entre Task 8, 11.

---

**Plan completo y guardado en `docs/superpowers/plans/2026-08-08-cierre-cuenta-tickets.md`.**
