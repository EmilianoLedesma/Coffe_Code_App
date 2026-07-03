# Ingredientes CRUD completo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoy `api/app/routers/ingredientes.py` solo tiene `GET` (list), `POST` (create) y `PUT /{id}/stock` (delta de stock). No hay forma de corregir `nombre`/`unidad`/`stock_minimo`/`costo_unitario` después de creado, ni de dar de baja un ingrediente. Este plan cierra esos 3 gaps sin tocar el endpoint de stock existente.

**Architecture:** Mismo patrón que `productos.py`: soft-delete vía `activo`, filtro `activo=True` por default en el listado, edición completa vía `PUT /{id}` separado del ajuste de stock (`PUT /{id}/stock` sigue siendo delta, no se toca).

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic (API), Flask + Jinja2 + Alpine.js (web-admin), pytest (ambos lados).

## Global Constraints

- `PUT /ingredientes/{id}/stock` sigue siendo un ajuste por delta (no absoluto) — no cambiar su comportamiento ni su firma.
- Roles: lectura y escritura ambas restringidas a Cocinero + Administrador (igual que hoy).
- Cada endpoint nuevo debe tener su request de Postman.

---

### Task 1: `GET /ingredientes/{id}`, `PUT /ingredientes/{id}`, deactivate, y filtro `activo` en el listado

**Files:**
- Modify: `api/app/models/ingredientes.py` (agregar `IngredienteUpdate`)
- Modify: `api/app/routers/ingredientes.py`
- Test: `api/app/tests/test_router_ingredientes.py`

**Interfaces:**
- Produces: `GET /ingredientes/{id}` → 200 `IngredienteOut` | 404; `PUT /ingredientes/{id}` → 200 `IngredienteOut` (edita nombre/unidad/stock_minimo/costo_unitario, NO stock_actual); `PUT /ingredientes/{id}/desactivar` → 200 `IngredienteOut` (pone `activo=False`); `GET /ingredientes` filtra por default solo `activo=True`.

- [ ] **Step 1: Leer el archivo de test actual**

Run: `cat api/app/tests/test_router_ingredientes.py` (si no existe, crearlo desde cero siguiendo el patrón de `test_router_categorias.py`: fixture `_token(catalogos, rol)` con `create_access_token`).

- [ ] **Step 2: Agregar el modelo `IngredienteUpdate`**

En `api/app/models/ingredientes.py`, agregar después de `IngredienteCreate`:

```python
class IngredienteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    unidad: str | None = Field(default=None, min_length=1, max_length=20)
    stock_minimo: Decimal | None = Field(default=None, ge=0)
    costo_unitario: Decimal | None = Field(default=None, gt=0)
```

(Deliberadamente sin `stock_actual` ni `activo` — stock se mueve solo por `/stock`, activo se mueve solo por `/desactivar`, para no mezclar semánticas.)

- [ ] **Step 3: Escribir los tests que deben fallar**

Agregar a `api/app/tests/test_router_ingredientes.py`:

```python
from app.core.constants import RolNombre
from app.data.ingredientes import Ingrediente
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


def test_listar_ingredientes_excluye_inactivos_por_default(client, db_session, catalogos):
    db_session.add_all(
        [
            Ingrediente(nombre="Leche", unidad="ml", stock_actual=500, stock_minimo=100, costo_unitario="0.02", activo=True),
            Ingrediente(nombre="Descontinuado", unidad="g", stock_actual=0, stock_minimo=0, costo_unitario="0.01", activo=False),
        ]
    )
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get("/ingredientes", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    nombres = [i["nombre"] for i in respuesta.json()]
    assert nombres == ["Leche"]


def test_obtener_ingrediente_por_id(client, db_session, catalogos):
    ingrediente = Ingrediente(nombre="Café molido", unidad="g", stock_actual=1000, stock_minimo=200, costo_unitario="0.05", activo=True)
    db_session.add(ingrediente)
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get(f"/ingredientes/{ingrediente.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Café molido"


def test_obtener_ingrediente_inexistente_404(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get("/ingredientes/9999", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 404


def test_editar_ingrediente_no_toca_stock_actual(client, db_session, catalogos):
    ingrediente = Ingrediente(nombre="Azucar", unidad="g", stock_actual=500, stock_minimo=100, costo_unitario="0.01", activo=True)
    db_session.add(ingrediente)
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.put(
        f"/ingredientes/{ingrediente.id}",
        json={"nombre": "Azúcar refinada", "costo_unitario": "0.015"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Azúcar refinada"
    assert float(cuerpo["costo_unitario"]) == 0.015
    assert float(cuerpo["stock_actual"]) == 500.0


def test_desactivar_ingrediente(client, db_session, catalogos):
    ingrediente = Ingrediente(nombre="Vainilla", unidad="ml", stock_actual=50, stock_minimo=10, costo_unitario="0.1", activo=True)
    db_session.add(ingrediente)
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.put(f"/ingredientes/{ingrediente.id}/desactivar", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
```

- [ ] **Step 4: Correr los tests, verificar que fallan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_ingredientes.py -v`
Expected: FAIL (rutas no existen, listado no filtra `activo`)

- [ ] **Step 5: Implementar**

Reemplazar `api/app/routers/ingredientes.py` completo:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.ingredientes import Ingrediente
from app.models.ingredientes import (
    ActualizarStock,
    IngredienteCreate,
    IngredienteOut,
    IngredienteUpdate,
)
from app.security.auth import require_rol

router = APIRouter(prefix="/ingredientes", tags=["ingredientes"])

_lectura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)
_escritura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)


def _get_ingrediente_o_404(db: Session, ingrediente_id: int) -> Ingrediente:
    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingrediente no encontrado")
    return ingrediente


@router.get("", response_model=list[IngredienteOut])
def listar(db: Session = Depends(get_db), _=Depends(_lectura)) -> list[Ingrediente]:
    return (
        db.query(Ingrediente)
        .filter(Ingrediente.activo.is_(True))
        .order_by(Ingrediente.nombre)
        .all()
    )


@router.get("/{ingrediente_id}", response_model=IngredienteOut)
def obtener(
    ingrediente_id: int, db: Session = Depends(get_db), _=Depends(_lectura)
) -> Ingrediente:
    return _get_ingrediente_o_404(db, ingrediente_id)


@router.post("", response_model=IngredienteOut, status_code=status.HTTP_201_CREATED)
def crear(datos: IngredienteCreate, db: Session = Depends(get_db), _=Depends(_escritura)) -> Ingrediente:
    ingrediente = Ingrediente(**datos.model_dump())
    db.add(ingrediente)
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


@router.put("/{ingrediente_id}", response_model=IngredienteOut)
def actualizar(
    ingrediente_id: int,
    datos: IngredienteUpdate,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> Ingrediente:
    ingrediente = _get_ingrediente_o_404(db, ingrediente_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(ingrediente, campo, valor)
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


@router.put("/{ingrediente_id}/desactivar", response_model=IngredienteOut)
def desactivar(
    ingrediente_id: int, db: Session = Depends(get_db), _=Depends(_escritura)
) -> Ingrediente:
    ingrediente = _get_ingrediente_o_404(db, ingrediente_id)
    ingrediente.activo = False
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


@router.put("/{ingrediente_id}/stock", response_model=IngredienteOut)
def actualizar_stock(
    ingrediente_id: int,
    datos: ActualizarStock,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> Ingrediente:
    ingrediente = _get_ingrediente_o_404(db, ingrediente_id)
    nuevo_stock = ingrediente.stock_actual + datos.cantidad
    if nuevo_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El ajuste dejaría el stock en negativo",
        )
    ingrediente.stock_actual = nuevo_stock
    db.commit()
    db.refresh(ingrediente)
    return ingrediente
```

**Importante — orden de rutas:** `/{ingrediente_id}` (GET) debe declararse ANTES de que FastAPI intente matchear rutas más específicas; como aquí todas las rutas con sufijo (`/desactivar`, `/stock`) son más específicas que `/{ingrediente_id}` puro, FastAPI las prioriza correctamente sin importar el orden de declaración en este caso (son paths distintos, no hay ambigüedad real). No se requiere reordenar.

- [ ] **Step 6: Correr los tests, verificar que pasan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_ingredientes.py -v`
Expected: PASS

- [ ] **Step 7: Correr toda la suite de la API**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde (revisar en particular que ningún otro test dependa de que `listar()` devuelva ingredientes inactivos)

- [ ] **Step 8: Commit**

```bash
git add api/app/models/ingredientes.py api/app/routers/ingredientes.py api/app/tests/test_router_ingredientes.py
git commit -m "feat(api): agregar get-one, edicion completa y desactivar en ingredientes"
```

---

### Task 2: Editar y desactivar ingredientes desde web-admin

**Files:**
- Modify: `web-admin/app/api_client.py` (agregar `actualizar_ingrediente`, `desactivar_ingrediente`)
- Modify: `web-admin/app/blueprints/ingredientes.py`
- Modify: `web-admin/app/templates/ingredientes.html`
- Test: `web-admin/tests/test_ingredientes.py`

**Interfaces:**
- Consumes: `PUT /ingredientes/{id}`, `PUT /ingredientes/{id}/desactivar` (Task 1).
- Produces: rutas `ingredientes.editar` (POST `/ingredientes/<id>/editar`), `ingredientes.desactivar` (POST `/ingredientes/<id>/desactivar`).

- [ ] **Step 1: Escribir los tests que deben fallar**

Agregar a `web-admin/tests/test_ingredientes.py`:

```python
@responses.activate
def test_editar_ingrediente(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/ingredientes/1",
        json={"id": 1, "nombre": "Leche deslactosada"},
        status=200,
    )

    respuesta = client.post(
        "/ingredientes/1/editar",
        data={"nombre": "Leche deslactosada", "unidad": "ml", "stock_minimo": "1000", "costo_unitario": "0.03"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "PUT"


@responses.activate
def test_desactivar_ingrediente(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/ingredientes/1/desactivar",
        json={"id": 1, "activo": False},
        status=200,
    )

    respuesta = client.post("/ingredientes/1/desactivar", follow_redirects=False)

    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "PUT"
    assert responses.calls[-1].request.url.endswith("/ingredientes/1/desactivar")
```

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_ingredientes.py -v`
Expected: FAIL con 404 (rutas Flask no existen)

- [ ] **Step 3: Implementar**

En `web-admin/app/api_client.py`, agregar junto a `ajustar_stock_ingrediente`:

```python
def actualizar_ingrediente(base_url: str, token: str, ingrediente_id: int, payload: dict) -> dict:
    return _request("PUT", base_url, f"/ingredientes/{ingrediente_id}", token=token, json=payload)


def desactivar_ingrediente(base_url: str, token: str, ingrediente_id: int) -> dict:
    return _request("PUT", base_url, f"/ingredientes/{ingrediente_id}/desactivar", token=token)
```

En `web-admin/app/blueprints/ingredientes.py`, agregar al final (y actualizar el import):

```python
from app.api_client import (
    ApiError,
    actualizar_ingrediente,
    ajustar_stock_ingrediente,
    crear_ingrediente,
    desactivar_ingrediente,
    listar_ingredientes,
)
```

```python
@bp.route("/<int:ingrediente_id>/editar", methods=["POST"])
@login_required
def editar(ingrediente_id: int):
    payload = {
        "nombre": request.form["nombre"],
        "unidad": request.form["unidad"],
        "stock_minimo": request.form["stock_minimo"],
        "costo_unitario": request.form["costo_unitario"],
    }
    try:
        actualizar_ingrediente(api_base_url(), current_token(), ingrediente_id, payload)
        flash("Ingrediente actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar el ingrediente: {error.detail}", "error")
    return redirect(url_for("ingredientes.listar"))


@bp.route("/<int:ingrediente_id>/desactivar", methods=["POST"])
@login_required
def desactivar(ingrediente_id: int):
    try:
        desactivar_ingrediente(api_base_url(), current_token(), ingrediente_id)
        flash("Ingrediente desactivado.", "success")
    except ApiError as error:
        flash(f"No se pudo desactivar el ingrediente: {error.detail}", "error")
    return redirect(url_for("ingredientes.listar"))
```

En `web-admin/app/templates/ingredientes.html`, dentro de la última `<td class="text-right">` de la fila, agregar junto al botón "Ajustar stock":

```html
            <button
              @click='modalEditar = {{ {
                "id": ingrediente.id,
                "nombre": ingrediente.nombre,
                "unidad": ingrediente.unidad,
                "stock_minimo": ingrediente.stock_minimo,
                "costo_unitario": ingrediente.costo_unitario,
              } | tojson }}'
              class="btn-link">Editar</button>
            <form action="{{ url_for('ingredientes.desactivar', ingrediente_id=ingrediente.id) }}" method="post" class="inline" onsubmit="return confirm('¿Desactivar este ingrediente?');">
              <button type="submit" class="btn-link-danger">Desactivar</button>
            </form>
```

Agregar `modalEditar: null` al `x-data` raíz del template (junto a `modalAbierto`/`modalStock`), y un nuevo modal (mismo patrón que el de "Ajustar stock") con un form que apunte a `` `/ingredientes/${modalEditar.id}/editar` `` con los 4 campos editables precargados desde `modalEditar`.

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_ingredientes.py -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite de web-admin**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde

- [ ] **Step 6: Commit**

```bash
git add web-admin/app/api_client.py web-admin/app/blueprints/ingredientes.py web-admin/app/templates/ingredientes.html web-admin/tests/test_ingredientes.py
git commit -m "feat(web-admin): editar y desactivar ingredientes desde el panel"
```

---

### Task 3: Postman

**Files:**
- Modify: `postman/coffee-code.postman_collection.json`

- [ ] **Step 1: Agregar 2 requests** en la carpeta donde ya viven las de ingredientes: "Actualizar Ingrediente" (PUT `{{base_url}}/ingredientes/1`, body con nombre/unidad/stock_minimo/costo_unitario, header `Authorization: Bearer {{token_cocinero}}`) y "Desactivar Ingrediente" (PUT `{{base_url}}/ingredientes/1/desactivar`, mismo header, sin body).

- [ ] **Step 2: Validar JSON**

Run: `python -c "import json; json.load(open('postman/coffee-code.postman_collection.json', encoding='utf-8'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add postman/coffee-code.postman_collection.json
git commit -m "docs(postman): agregar requests de actualizar/desactivar ingrediente"
```
