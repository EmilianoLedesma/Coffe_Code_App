# Usuarios: /api/roles + reset de contraseña Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar dos gaps reales encontrados por audit: (1) el panel web no puede resetear la contraseña de un usuario aunque la API ya lo soporta vía `PUT /api/usuarios/{id}`; (2) no existe `GET /api/roles`, así que el web-admin harcodea `ROL_ID_POR_NOMBRE = {"Mesero": 1, ...}` asumiendo que los IDs de rol coinciden con el orden de inserción del seed — frágil si el seed cambia.

**Architecture:** `RolOut` ya existe en `api/app/models/usuarios.py` — solo falta exponer un router de lectura. El backend de `actualizar_usuario` (`api/app/services/usuarios.py:40-66`) ya maneja `password` opcional correctamente (lo excluye de `exclude_unset` y lo aplica aparte solo si viene). El único cambio real de comportamiento está en el template/blueprint del web-admin.

**Tech Stack:** FastAPI + Pydantic (API), Flask + Jinja2 + Alpine.js (web-admin), pytest (ambos lados).

## Global Constraints

- JWT en `Authorization: Bearer {token}`. Roles válidos: Mesero, Cajero, Cocinero, Administrador.
- Password nunca se expone en `UsuarioOut` — no cambiar eso.
- Cada endpoint nuevo debe tener su request de Postman.

---

### Task 1: Endpoint `GET /api/roles`

**Files:**
- Create: `api/app/routers/roles.py`
- Modify: `api/app/main.py` (registrar el router — buscar dónde se incluyen los demás `include_router`)
- Test: `api/app/tests/test_router_roles.py`

**Interfaces:**
- Consumes: `Rol` (`api/app/data/roles.py`), `RolOut` (`api/app/models/usuarios.py`, ya existe).
- Produces: `GET /api/roles` → 200 `list[RolOut]`. Cualquier rol autenticado puede leerlo (es un catálogo, no un dato sensible).

- [ ] **Step 1: Escribir el test que debe fallar**

Crear `api/app/tests/test_router_roles.py`:

```python
from app.core.constants import RolNombre
from app.security.auth import create_access_token


def test_listar_roles(client, db_session, catalogos):
    token = create_access_token(user_id=1, rol=RolNombre.MESERO)
    respuesta = client.get("/api/roles", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    nombres = {r["nombre"] for r in respuesta.json()}
    assert nombres == {"Mesero", "Cajero", "Cocinero", "Administrador"}


def test_listar_roles_requiere_autenticacion(client, db_session, catalogos):
    respuesta = client.get("/api/roles")
    assert respuesta.status_code == 401
```

- [ ] **Step 2: Correr el test, verificar que falla**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_roles.py -v`
Expected: FAIL con 404 (la ruta no existe)

- [ ] **Step 3: Implementar el router**

Crear `api/app/routers/roles.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data.db import get_db
from app.data.roles import Rol
from app.models.usuarios import RolOut
from app.security.auth import get_current_user

router = APIRouter(prefix="/api", tags=["roles"])


@router.get("/roles", response_model=list[RolOut])
def listar_roles(db: Session = Depends(get_db), _=Depends(get_current_user)) -> list[Rol]:
    return db.query(Rol).order_by(Rol.id).all()
```

Verificar el nombre exacto de la dependencia de autenticación básica (sin rol específico) en `api/app/security/auth.py` — si se llama distinto a `get_current_user`, usar el nombre real encontrado ahí.

En `api/app/main.py`, agregar junto a los demás `app.include_router(...)`:

```python
from app.routers.roles import router as roles_router
```
```python
app.include_router(roles_router)
```

- [ ] **Step 4: Correr el test, verificar que pasa**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_roles.py -v`
Expected: PASS (2/2)

- [ ] **Step 5: Correr toda la suite de la API**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/roles.py api/app/main.py api/app/tests/test_router_roles.py
git commit -m "feat(api): agregar GET /api/roles"
```

---

### Task 2: web-admin deja de hardcodear roles

**Files:**
- Modify: `web-admin/app/api_client.py` (agregar `listar_roles`)
- Modify: `web-admin/app/blueprints/usuarios.py` (quitar `ROL_ID_POR_NOMBRE`, usar `listar_roles`)
- Modify: `web-admin/app/templates/usuarios.html` (el `<select>` de rol usa `rol.id`/`rol.nombre` en vez de `loop.index`)
- Test: `web-admin/tests/test_usuarios.py`

**Interfaces:**
- Consumes: `GET /api/roles` (Task 1).
- Produces: `listar_roles(base_url, token) -> list[dict]` en `api_client.py`.

- [ ] **Step 1: Leer el test actual para no romper convenciones**

Run: `cat web-admin/tests/test_usuarios.py` — revisar cómo se mockea hoy `listar_usuarios`/`crear_usuario` para replicar el mismo estilo con `listar_roles`.

- [ ] **Step 2: Escribir/ajustar los tests que deben fallar**

Agregar a `web-admin/tests/test_usuarios.py` (ajustar el mock de `GET /categorias`-style ya usado en el archivo si aplica):

```python
@responses.activate
def test_listar_usuarios_usa_roles_de_la_api(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/roles",
        json=[
            {"id": 1, "nombre": "Mesero"},
            {"id": 2, "nombre": "Cajero"},
            {"id": 3, "nombre": "Cocinero"},
            {"id": 4, "nombre": "Administrador"},
        ],
        status=200,
    )
    responses.add(responses.GET, f"{BASE_URL}/api/usuarios", json=[], status=200)

    respuesta = client.get("/usuarios")

    assert respuesta.status_code == 200
    assert responses.calls[0].request.url.endswith("/api/roles")


@responses.activate
def test_editar_usuario_envia_password_si_se_captura(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/usuarios/1",
        json={"id": 1, "nombre": "Ana"},
        status=200,
    )

    respuesta = client.post(
        "/usuarios/1/editar",
        data={
            "nombre": "Ana",
            "apellido_paterno": "Ruiz",
            "apellido_materno": "",
            "correo_electronico": "ana@coffeecode.com",
            "id_rol": "1",
            "password": "NuevaClave123!",
        },
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    import json

    cuerpo_enviado = json.loads(responses.calls[-1].request.body)
    assert cuerpo_enviado["password"] == "NuevaClave123!"


@responses.activate
def test_editar_usuario_sin_password_no_la_envia(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/usuarios/1",
        json={"id": 1, "nombre": "Ana"},
        status=200,
    )

    respuesta = client.post(
        "/usuarios/1/editar",
        data={
            "nombre": "Ana",
            "apellido_paterno": "Ruiz",
            "apellido_materno": "",
            "correo_electronico": "ana@coffeecode.com",
            "id_rol": "1",
            "password": "",
        },
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    import json

    cuerpo_enviado = json.loads(responses.calls[-1].request.body)
    assert "password" not in cuerpo_enviado
```

Nota: revisar si `web-admin/tests/test_usuarios.py` ya tiene un fixture `client`/`_login_como_admin` propio (siguiendo el mismo patrón visto en `test_productos.py`/`test_ingredientes.py`) — reusar ese, no duplicar.

- [ ] **Step 3: Correr los tests, verificar que fallan**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_usuarios.py -v`
Expected: FAIL (la ruta `/usuarios` actual no llama a `/api/roles`; el payload de editar no distingue password vacío)

- [ ] **Step 4: Implementar**

En `web-admin/app/api_client.py`, agregar junto a `listar_usuarios`:

```python
def listar_roles(base_url: str, token: str) -> list[dict]:
    return _request("GET", base_url, "/api/roles", token=token)
```

Reemplazar `web-admin/app/blueprints/usuarios.py` completo:

```python
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import ApiError, actualizar_usuario, crear_usuario, listar_roles, listar_usuarios
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@bp.route("")
@login_required
def listar():
    token = current_token()
    base_url = api_base_url()
    usuarios = listar_usuarios(base_url, token)
    roles = listar_roles(base_url, token)
    return render_template("usuarios.html", usuarios=usuarios, roles=roles)


@bp.route("/nuevo", methods=["POST"])
@login_required
def crear():
    payload = {
        "nombre": request.form["nombre"],
        "apellido_paterno": request.form["apellido_paterno"],
        "apellido_materno": request.form.get("apellido_materno") or None,
        "correo_electronico": request.form["correo_electronico"],
        "password": request.form["password"],
        "id_rol": int(request.form["id_rol"]),
    }
    try:
        crear_usuario(api_base_url(), current_token(), payload)
        flash("Usuario creado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo crear el usuario: {error.detail}", "error")
    return redirect(url_for("usuarios.listar"))


@bp.route("/<int:usuario_id>/editar", methods=["POST"])
@login_required
def editar(usuario_id: int):
    payload = {
        "nombre": request.form["nombre"],
        "apellido_paterno": request.form["apellido_paterno"],
        "apellido_materno": request.form.get("apellido_materno") or None,
        "correo_electronico": request.form["correo_electronico"],
        "id_rol": int(request.form["id_rol"]),
        "activo": request.form.get("activo") == "on",
    }
    nueva_password = request.form.get("password") or ""
    if nueva_password:
        payload["password"] = nueva_password
    try:
        actualizar_usuario(api_base_url(), current_token(), usuario_id, payload)
        flash("Usuario actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar el usuario: {error.detail}", "error")
    return redirect(url_for("usuarios.listar"))
```

En `web-admin/app/templates/usuarios.html`, reemplazar el bloque del `<select>` de rol y el bloque de password:

```html
        <select class="input-field" name="id_rol" required>
          {% for rol in roles %}
          <option value="{{ rol.id }}" x-bind:selected="editando && editando.id_rol === {{ rol.id }}">{{ rol.nombre }}</option>
          {% endfor %}
        </select>
        <input class="input-field" type="password" name="password" :placeholder="editando ? 'Nueva contraseña (dejar vacío para no cambiar)' : 'Contraseña'" :required="!editando">
```

(quitar el `<template x-if="!editando">...</template>` que envolvía el campo de password — ahora el mismo input sirve para crear y editar, y también ajustar el atributo `id_rol` guardado en `editando` en el botón "Editar" de la tabla, que ya usa `usuario.rol.id` — no requiere cambio ahí).

- [ ] **Step 5: Correr los tests, verificar que pasan**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest tests/test_usuarios.py -v`
Expected: PASS

- [ ] **Step 6: Correr toda la suite de web-admin**

Run: `cd web-admin && .venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests existentes siguen en verde

- [ ] **Step 7: Commit**

```bash
git add web-admin/app/api_client.py web-admin/app/blueprints/usuarios.py web-admin/app/templates/usuarios.html web-admin/tests/test_usuarios.py
git commit -m "fix(web-admin): roles dinamicos via /api/roles y reset de password en edicion"
```

---

### Task 3: Postman

**Files:**
- Modify: `postman/coffee-code.postman_collection.json`

- [ ] **Step 1: Agregar 1 request "Listar Roles"** (GET `{{base_url}}/api/roles`, header `Authorization: Bearer {{token_admin}}`) en la carpeta de Admin/Usuarios existente.

- [ ] **Step 2: Validar JSON**

Run: `python -c "import json; json.load(open('postman/coffee-code.postman_collection.json', encoding='utf-8'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add postman/coffee-code.postman_collection.json
git commit -m "docs(postman): agregar request de listar roles"
```
