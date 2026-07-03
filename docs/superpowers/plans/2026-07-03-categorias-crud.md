# Categorías CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir crear, editar y desactivar categorías de producto desde la API y desde el panel web-admin (hoy solo existe `GET /categorias`).

**Architecture:** Seguir exactamente el patrón ya usado por `api/app/routers/productos.py` (soft-delete vía `activo`, gated a Administrador para escritura, lectura abierta a los 4 roles) y por `web-admin/app/blueprints/productos.py` (modal crear/editar con Alpine.js).

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic (API), Flask + Jinja2 + Alpine.js (web-admin), pytest (ambos lados).

## Global Constraints

- Nombres de campos/tablas en español, tal cual el diccionario de datos en `.claude/CLAUDE.md`.
- Autorización por rol vía middleware (`require_rol`), no solo en frontend.
- Cada endpoint nuevo debe tener su request de Postman (`postman/coffee-code.postman_collection.json`).
- No se reintroduce DELETE físico — `Producto.id_categoria` es FK NOT NULL, así que categorías solo se desactivan (`activo=False`), nunca se borran.

---

### Task 1: Modelos Pydantic `CategoriaCreate`/`CategoriaUpdate`

**Files:**
- Modify: `api/app/models/productos.py` (agregar clases junto a `CategoriaOut`, línea ~6)

**Interfaces:**
- Produces: `CategoriaCreate(nombre: str, descripcion: str | None = None)`, `CategoriaUpdate(nombre: str | None = None, descripcion: str | None = None, activo: bool | None = None)` — consumidos por Task 2.

- [ ] **Step 1: Agregar las clases**

En `api/app/models/productos.py`, justo después de `CategoriaOut`:

```python
class CategoriaCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str | None = Field(default=None, max_length=255)


class CategoriaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    descripcion: str | None = Field(default=None, max_length=255)
    activo: bool | None = None
```

- [ ] **Step 2: Verificar que importa sin errores**

Run: `cd api && ./.venv/Scripts/python.exe -c "from app.models.productos import CategoriaCreate, CategoriaUpdate; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add api/app/models/productos.py
git commit -m "feat(api): agregar modelos CategoriaCreate/CategoriaUpdate"
```

---

### Task 2: Endpoints `POST /categorias` y `PUT /categorias/{id}`

**Files:**
- Modify: `api/app/routers/categorias.py`
- Test: `api/app/tests/test_router_categorias.py`

**Interfaces:**
- Consumes: `CategoriaCreate`, `CategoriaUpdate` (Task 1); `Categoria` (`api/app/data/categorias.py`); `require_rol` (`api/app/security/auth.py`).
- Produces: `POST /categorias` → 201 `CategoriaOut`; `PUT /categorias/{id}` → 200 `CategoriaOut` o 404.

- [ ] **Step 1: Escribir los tests que deben fallar**

Agregar al final de `api/app/tests/test_router_categorias.py`:

```python
def test_crear_categoria_requiere_admin(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.COCINERO)
    respuesta = client.post(
        "/categorias",
        json={"nombre": "Postres"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 403


def test_crear_categoria_como_admin(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.post(
        "/categorias",
        json={"nombre": "Postres", "descripcion": "Panque, pay, etc."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Postres"


def test_actualizar_categoria_desactiva(client, db_session, catalogos):
    categoria = Categoria(nombre="Snacks", activo=True)
    db_session.add(categoria)
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.put(
        f"/categorias/{categoria.id}",
        json={"activo": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Snacks"

    # una vez desactivada, listar() ya no debe incluirla
    respuesta_listar = client.get("/categorias", headers={"Authorization": f"Bearer {token}"})
    assert "Snacks" not in [c["nombre"] for c in respuesta_listar.json()]


def test_actualizar_categoria_inexistente_404(client, db_session, catalogos):
    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.put(
        "/categorias/9999",
        json={"nombre": "No existe"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 404
```

Nota: `CategoriaOut` (usado como `response_model`) solo expone `id`/`nombre` hoy — eso es correcto y no cambia en este plan.

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_categorias.py -v`
Expected: FAIL (404 en vez de 201/200 en los tests nuevos — las rutas no existen)

- [ ] **Step 3: Implementar los endpoints**

Reemplazar el contenido completo de `api/app/routers/categorias.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.data.db import get_db
from app.models.productos import CategoriaCreate, CategoriaOut, CategoriaUpdate
from app.security.auth import require_rol

router = APIRouter(prefix="/categorias", tags=["categorias"])

_lectura = require_rol(
    RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR
)
_escritura = require_rol(RolNombre.ADMINISTRADOR)


def _get_categoria_o_404(db: Session, categoria_id: int) -> Categoria:
    categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    return categoria


@router.get("", response_model=list[CategoriaOut])
def listar(db: Session = Depends(get_db), _=Depends(_lectura)) -> list[Categoria]:
    return (
        db.query(Categoria)
        .filter(Categoria.activo.is_(True))
        .order_by(Categoria.nombre)
        .all()
    )


@router.post("", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
def crear(datos: CategoriaCreate, db: Session = Depends(get_db), _=Depends(_escritura)) -> Categoria:
    categoria = Categoria(**datos.model_dump())
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.put("/{categoria_id}", response_model=CategoriaOut)
def actualizar(
    categoria_id: int,
    datos: CategoriaUpdate,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> Categoria:
    categoria = _get_categoria_o_404(db, categoria_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(categoria, campo, valor)
    db.commit()
    db.refresh(categoria)
    return categoria
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_categorias.py -v`
Expected: PASS (6/6)

- [ ] **Step 5: Correr toda la suite de la API para descartar regresiones**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/categorias.py api/app/tests/test_router_categorias.py
git commit -m "feat(api): agregar POST/PUT /categorias (crear y desactivar)"
```

---

### Task 3: Página de gestión de categorías en web-admin

**Files:**
- Modify: `web-admin/app/api_client.py` (agregar `crear_categoria`, `actualizar_categoria`)
- Create: `web-admin/app/blueprints/categorias.py`
- Create: `web-admin/app/templates/categorias.html`
- Modify: `web-admin/app/templates/base.html` (nav link)
- Modify: `web-admin/app/__init__.py` (registrar blueprint)
- Test: `web-admin/tests/test_categorias.py`

**Interfaces:**
- Consumes: `listar_categorias` (ya existe en `api_client.py`), patrón de `web-admin/app/blueprints/productos.py`.
- Produces: rutas `categorias.listar` (GET `/categorias`), `categorias.crear` (POST `/categorias/nuevo`), `categorias.editar` (POST `/categorias/<id>/editar`).

- [ ] **Step 1: Agregar funciones al api_client**

En `web-admin/app/api_client.py`, junto a `listar_categorias` (buscar con grep si no se conoce la línea exacta):

```python
def crear_categoria(base_url: str, token: str, payload: dict) -> dict:
    return _request("POST", base_url, "/categorias", token=token, json=payload)


def actualizar_categoria(base_url: str, token: str, categoria_id: int, payload: dict) -> dict:
    return _request("PUT", base_url, f"/categorias/{categoria_id}", token=token, json=payload)
```

- [ ] **Step 2: Escribir el test que debe fallar**

Crear `web-admin/tests/test_categorias.py`:

```python
import importlib

import pytest
import responses

from app.blueprints.categorias import bp as categorias_bp

BASE_URL = "http://testserver"


@pytest.fixture()
def client(app):
    if "categorias" not in app.blueprints:
        app.register_blueprint(categorias_bp)
    for nombre in ("usuarios", "productos", "ingredientes", "recetas"):
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
def test_listar_categorias(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/categorias",
        json=[{"id": 1, "nombre": "Bebidas calientes"}],
        status=200,
    )
    respuesta = client.get("/categorias")
    assert respuesta.status_code == 200
    assert b"Bebidas calientes" in respuesta.data


@responses.activate
def test_crear_categoria(client):
    _login_como_admin(client)
    responses.add(responses.GET, f"{BASE_URL}/categorias", json=[], status=200)
    responses.add(responses.POST, f"{BASE_URL}/categorias", json={"id": 2, "nombre": "Postres"}, status=201)

    respuesta = client.post(
        "/categorias/nuevo",
        data={"nombre": "Postres", "descripcion": ""},
        follow_redirects=False,
    )
    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "POST"


@responses.activate
def test_editar_categoria_desactiva(client):
    _login_como_admin(client)
    responses.add(responses.GET, f"{BASE_URL}/categorias", json=[], status=200)
    responses.add(responses.PUT, f"{BASE_URL}/categorias/1", json={"id": 1, "nombre": "Snacks"}, status=200)

    respuesta = client.post(
        "/categorias/1/editar",
        data={"nombre": "Snacks", "descripcion": "", "activo": "off"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "PUT"
```

- [ ] **Step 3: Correr el test, verificar que falla**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_categorias.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.blueprints.categorias'`

- [ ] **Step 4: Crear el blueprint**

Crear `web-admin/app/blueprints/categorias.py`:

```python
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import ApiError, actualizar_categoria, crear_categoria, listar_categorias
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("categorias", __name__, url_prefix="/categorias")


@bp.route("")
@login_required
def listar():
    categorias = listar_categorias(api_base_url(), current_token())
    return render_template("categorias.html", categorias=categorias)


def _payload_desde_formulario() -> dict:
    return {
        "nombre": request.form["nombre"],
        "descripcion": request.form.get("descripcion") or None,
    }


@bp.route("/nuevo", methods=["POST"])
@login_required
def crear():
    try:
        crear_categoria(api_base_url(), current_token(), _payload_desde_formulario())
        flash("Categoría creada correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo crear la categoría: {error.detail}", "error")
    return redirect(url_for("categorias.listar"))


@bp.route("/<int:categoria_id>/editar", methods=["POST"])
@login_required
def editar(categoria_id: int):
    payload = _payload_desde_formulario()
    payload["activo"] = request.form.get("activo") == "on"
    try:
        actualizar_categoria(api_base_url(), current_token(), categoria_id, payload)
        flash("Categoría actualizada correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar la categoría: {error.detail}", "error")
    return redirect(url_for("categorias.listar"))
```

- [ ] **Step 5: Crear el template**

Crear `web-admin/app/templates/categorias.html` (mismo patrón visual que `productos.html`):

```html
{% extends "base.html" %}
{% block title %}Categorías — Coffee Code Admin{% endblock %}
{% block content %}
<div x-data="{ modalAbierto: false, editando: null }">
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-semibold text-starbucks">Categorías de producto</h1>
    <button @click="modalAbierto = true; editando = null" class="btn btn-primary">
      + Nueva categoría
    </button>
  </div>

  <div class="card overflow-hidden">
    <table class="data-table">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Descripción</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {% for categoria in categorias %}
        <tr>
          <td>{{ categoria.nombre }}</td>
          <td>{{ categoria.descripcion or "—" }}</td>
          <td class="text-right">
            <button
              @click='modalAbierto = true; editando = {{ {
                "id": categoria.id,
                "nombre": categoria.nombre,
                "descripcion": categoria.descripcion or "",
              } | tojson }}'
              class="btn-link">Editar</button>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div x-show="modalAbierto" x-cloak class="fixed inset-0 modal-overlay flex items-center justify-center z-50">
    <div class="modal-panel p-6 w-full max-w-md" @click.outside="modalAbierto = false">
      <h2 class="text-lg font-semibold text-starbucks mb-4" x-text="editando ? 'Editar categoría' : 'Nueva categoría'"></h2>
      <form :action="editando ? `/categorias/${editando.id}/editar` : '/categorias/nuevo'" method="post" class="space-y-3">
        <input class="input-field" name="nombre" placeholder="Nombre" :value="editando ? editando.nombre : ''" required>
        <textarea class="input-field" name="descripcion" placeholder="Descripción (opcional)" x-text="editando ? editando.descripcion : ''"></textarea>
        <template x-if="editando">
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" name="activo" checked> Activa
          </label>
        </template>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="modalAbierto = false" class="btn btn-ghost">Cancelar</button>
          <button type="submit" class="btn btn-primary">Guardar</button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Registrar el blueprint y el nav link**

En `web-admin/app/__init__.py`, agregar el import y registro junto a `productos_bp`:

```python
    from app.blueprints.categorias import bp as categorias_bp
```
```python
    app.register_blueprint(categorias_bp)
```

En `web-admin/app/templates/base.html`, agregar el link de nav junto al de Productos (línea ~39):

```html
      <a href="{{ url_for('categorias.listar') }}" class="nav-link {{ 'active' if request.endpoint and request.endpoint.startswith('categorias.') }}">Categorías</a>
```

- [ ] **Step 7: Correr los tests, verificar que pasan**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_categorias.py -v`
Expected: PASS (3/3)

- [ ] **Step 8: Correr toda la suite de web-admin**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde (el nuevo nav link no debe romper snapshots de otras páginas)

- [ ] **Step 9: Commit**

```bash
git add web-admin/app/api_client.py web-admin/app/blueprints/categorias.py web-admin/app/templates/categorias.html web-admin/app/templates/base.html web-admin/app/__init__.py web-admin/tests/test_categorias.py
git commit -m "feat(web-admin): agregar pagina de gestion de categorias"
```

---

### Task 4: Postman

**Files:**
- Modify: `postman/coffee-code.postman_collection.json`

- [ ] **Step 1: Agregar 2 requests a la carpeta "03 - Cocina"** (mismo grupo donde ya viven Listar/Crear/Actualizar Producto): "Crear Categoria" (POST `{{base_url}}/categorias`, body `{"nombre": "Postres", "descripcion": "Panque, pay"}`, header `Authorization: Bearer {{token_admin}}`) y "Actualizar Categoria" (PUT `{{base_url}}/categorias/1`, body `{"activo": false}`, mismo header). Seguir el formato JSON exacto de las requests vecinas ya existentes (copiar una y ajustar url/method/body).

- [ ] **Step 2: Validar que el JSON sigue siendo válido**

Run: `python -c "import json; json.load(open('postman/coffee-code.postman_collection.json', encoding='utf-8'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add postman/coffee-code.postman_collection.json
git commit -m "docs(postman): agregar requests de crear/actualizar categoria"
```
