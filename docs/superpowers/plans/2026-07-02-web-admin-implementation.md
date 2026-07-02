# Panel Web Admin (Flask) — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir `web-admin/` (Flask) completo — usuarios/roles, catálogo (productos/ingredientes/recetas) y un dashboard de reportes accionables con export PDF/XLSX — consumiendo la API FastAPI ya funcional, corriendo como servicio Docker adicional, con pruebas automatizadas.

**Architecture:** Flask 3 con blueprints por módulo, un `api_client.py` central que envuelve todas las llamadas HTTP a la API (con manejo de errores propio `ApiError`), sesión Flask firmada guardando el JWT, plantillas Jinja2 + Tailwind (Play CDN, sin build step) + Alpine.js para interactividad + Chart.js para gráficas. Dos endpoints nuevos se agregan a la API (categorías, lectura/borrado de recetas) siguiendo el estilo existente de routers, para que el panel pueda alimentar sus formularios de catálogo.

**Tech Stack:** Flask 3, requests, python-dotenv, WeasyPrint, openpyxl, pytest + pytest-flask-style monkeypatching, Tailwind CSS (Play CDN), Alpine.js (CDN), Chart.js (CDN). Backend: FastAPI/SQLAlchemy/Alembic ya existentes, sin cambios de patrón.

## Global Constraints

- Español para nombres de tablas, campos, mensajes de error y commits (CLAUDE.md).
- Flask/web-admin **no** accede a Postgres directamente ni implementa lógica de negocio nueva — solo consume la API y agrega/cruza respuestas ya autorizadas.
- JWT en `Authorization: Bearer {token}`, mismo formato que ya usa la API (`user_id`, `rol`, `exp: 24h`).
- Cada endpoint nuevo de la API debe acompañarse de su request de Postman (CLAUDE.md).
- Autorización por rol en cada endpoint protegido vía middleware, no solo en el frontend (CLAUDE.md) — el panel además revalida que el `rol` devuelto por `/auth/login` sea `Administrador` antes de crear sesión.
- Migraciones de DB versionadas con Alembic — este plan no agrega tablas nuevas, así que no aplica, pero si algún paso lo requiriera, no se usaría `create_all`.
- Variables de entorno vía `.env`, nunca hardcodeadas — mismo patrón que `api/.env` / `api/.env.example`.
- Seguir el estilo de código ya usado en `api/` (routers delgados, `require_rol`, `joinedload`, Pydantic `ConfigDict(from_attributes=True)`) al tocar la API.
- Nota de implementación: se usa Tailwind vía Play CDN (sin paso de build) para mantener el stack simple — sigue siendo Tailwind CSS real, solo sin compilación previa.

---

## Parte A — Ajustes a la API (FastAPI)

### Task 1: Endpoint `GET /categorias`

El panel necesita listar categorías activas para los formularios de productos (crear/editar requiere `id_categoria` válido, y hoy no hay forma de listarlas vía API).

**Files:**
- Create: `api/app/routers/categorias.py`
- Modify: `api/app/main.py` (registrar el router)
- Modify: `postman/coffee-code.postman_collection.json` (agregar request "Listar Categorias" dentro de "03 - Cocina")
- Test: `api/app/tests/test_router_categorias.py`

**Interfaces:**
- Consumes: `app.core.constants.RolNombre`, `app.security.auth.require_rol`, `app.data.categorias.Categoria`, `app.models.productos.CategoriaOut` (ya existe: `{id: int, nombre: str}`).
- Produces: `GET /categorias` → `200` con `list[CategoriaOut]`, ordenado por nombre, solo categorías `activo=True`. Roles permitidos: `Mesero, Cajero, Cocinero, Administrador` (mismo set que `GET /productos`).

- [ ] **Step 1: Escribir el router**

Crear `api/app/routers/categorias.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.data.db import get_db
from app.models.productos import CategoriaOut
from app.security.auth import require_rol

router = APIRouter(prefix="/categorias", tags=["categorias"])

_lectura = require_rol(
    RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR
)


@router.get("", response_model=list[CategoriaOut])
def listar(db: Session = Depends(get_db), _=Depends(_lectura)) -> list[Categoria]:
    return (
        db.query(Categoria)
        .filter(Categoria.activo.is_(True))
        .order_by(Categoria.nombre)
        .all()
    )
```

- [ ] **Step 2: Registrar el router en `main.py`**

En `api/app/main.py`, junto a los demás imports de routers:

```python
from app.routers.categorias import router as categorias_router
```

Y junto a los demás `app.include_router(...)`, antes de `admin_router`:

```python
app.include_router(categorias_router)
```

- [ ] **Step 3: Escribir el test**

Crear `api/app/tests/test_router_categorias.py`:

```python
from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


def test_listar_categorias_solo_activas(client, db_session, catalogos):
    db_session.add_all(
        [
            Categoria(nombre="Bebidas calientes", activo=True),
            Categoria(nombre="Descontinuada", activo=False),
        ]
    )
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get("/categorias", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    nombres = [c["nombre"] for c in respuesta.json()]
    assert nombres == ["Bebidas calientes"]


def test_listar_categorias_requiere_rol_valido(client, db_session, catalogos):
    respuesta = client.get("/categorias")
    assert respuesta.status_code == 403
```

- [ ] **Step 4: Correr los tests**

Run: `cd api && python -m pytest app/tests/test_router_categorias.py -v`
Expected: 2 tests PASS (requiere Postgres real corriendo, ver `TEST_ADMIN_DATABASE_URL` en `conftest.py` — con `docker compose up -d` ya activo, corre contra el Postgres de Docker en el puerto `5434`).

- [ ] **Step 5: Agregar el request de Postman**

Abrir `postman/coffee-code.postman_collection.json`. Dentro del array `item` de la carpeta `"03 - Cocina"` (empieza en la línea donde está `"name": "03 - Cocina"`), insertar este objeto justo después del item `"Listar Productos"` (antes de `"Crear Producto"`):

```json
{
  "name": "Listar Categorias",
  "request": {
    "method": "GET",
    "auth": {
      "type": "bearer",
      "bearer": [
        {
          "key": "token",
          "value": "{{token_cocinero}}"
        }
      ]
    },
    "url": {
      "raw": "{{base_url}}/categorias",
      "host": [
        "{{base_url}}"
      ],
      "path": [
        "categorias"
      ]
    }
  }
},
```

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/categorias.py api/app/main.py api/app/tests/test_router_categorias.py postman/coffee-code.postman_collection.json
git commit -m "feat(api): agregar endpoint GET /categorias"
```

---

### Task 2: Endpoints de lectura y borrado de recetas por producto

El panel necesita mostrar la receta actual de un producto (hoy solo se puede crear/actualizar, no listar ni borrar una asociación producto-ingrediente).

**Files:**
- Modify: `api/app/routers/recetas.py`
- Modify: `postman/coffee-code.postman_collection.json` (agregar "Listar Receta de un Producto" y "Eliminar Ingrediente de Receta" en "03 - Cocina")
- Test: `api/app/tests/test_router_recetas.py`

**Interfaces:**
- Consumes: `app.models.productos.RecetaOut` (ya existe), `app.data.recetas.Receta`, `app.data.productos.Producto`, `app.data.ingredientes.Ingrediente`, `require_rol`.
- Produces:
  - `GET /producto_ingrediente?producto_id={id}` → `200` con `list[RecetaOut]` (recetas del producto, con `ingrediente` embebido), roles `Cocinero, Administrador`.
  - `DELETE /producto_ingrediente/{producto_id}/{ingrediente_id}` → `204` si existía y se borró, `404` si no existía, roles `Cocinero, Administrador`.

- [ ] **Step 1: Escribir el test primero**

Crear `api/app/tests/test_router_recetas.py`:

```python
from decimal import Decimal

from app.core.constants import RolNombre
from app.data.categorias import Categoria
from app.data.ingredientes import Ingrediente
from app.data.productos import Producto
from app.data.recetas import Receta
from app.security.auth import create_access_token


def _token(catalogos, rol: str) -> str:
    return create_access_token(user_id=1, rol=catalogos["roles"][rol].nombre)


def _crear_producto_con_receta(db_session):
    categoria = Categoria(nombre="Bebidas calientes", activo=True)
    db_session.add(categoria)
    db_session.flush()

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


def test_listar_receta_de_producto(client, db_session, catalogos):
    producto, ingrediente = _crear_producto_con_receta(db_session)
    token = _token(catalogos, RolNombre.COCINERO)

    respuesta = client.get(
        f"/producto_ingrediente?producto_id={producto.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 1
    assert cuerpo[0]["id_ingrediente"] == ingrediente.id
    assert cuerpo[0]["ingrediente"]["nombre"] == "Leche entera"


def test_eliminar_receta_existente(client, db_session, catalogos):
    producto, ingrediente = _crear_producto_con_receta(db_session)
    token = _token(catalogos, RolNombre.COCINERO)

    respuesta = client.delete(
        f"/producto_ingrediente/{producto.id}/{ingrediente.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 204

    verificacion = client.get(
        f"/producto_ingrediente?producto_id={producto.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verificacion.json() == []


def test_eliminar_receta_inexistente_da_404(client, db_session, catalogos):
    producto, ingrediente = _crear_producto_con_receta(db_session)
    token = _token(catalogos, RolNombre.COCINERO)

    respuesta = client.delete(
        f"/producto_ingrediente/{producto.id}/9999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 404
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd api && python -m pytest app/tests/test_router_recetas.py -v`
Expected: FAIL (404 en `/producto_ingrediente?producto_id=` porque el método `GET` no existe todavía en ese path — la ruta actual solo acepta `POST`).

- [ ] **Step 3: Implementar los endpoints**

En `api/app/routers/recetas.py`, agregar imports y las dos rutas nuevas (mantener el `POST` existente tal cual):

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RolNombre
from app.data.db import get_db
from app.data.ingredientes import Ingrediente
from app.data.productos import Producto
from app.data.recetas import Receta
from app.models.productos import RecetaCreate, RecetaOut
from app.security.auth import require_rol

router = APIRouter(prefix="/producto_ingrediente", tags=["recetas"])

_lectura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)
_escritura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)


@router.get("", response_model=list[RecetaOut])
def listar_por_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(_lectura),
) -> list[Receta]:
    return (
        db.query(Receta)
        .options(joinedload(Receta.ingrediente))
        .filter(Receta.id_producto == producto_id)
        .all()
    )


@router.post("", response_model=RecetaOut, status_code=status.HTTP_201_CREATED)
def crear_receta(
    datos: RecetaCreate, db: Session = Depends(get_db), _=Depends(_escritura)
) -> Receta:
    producto = db.query(Producto).filter(Producto.id == datos.producto_id).first()
    if not producto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == datos.ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingrediente no encontrado")

    receta = (
        db.query(Receta)
        .filter(Receta.id_producto == datos.producto_id, Receta.id_ingrediente == datos.ingrediente_id)
        .first()
    )
    if receta:
        receta.cantidad_requerida = datos.cantidad
    else:
        receta = Receta(
            id_producto=datos.producto_id,
            id_ingrediente=datos.ingrediente_id,
            cantidad_requerida=datos.cantidad,
        )
        db.add(receta)

    db.commit()
    return (
        db.query(Receta)
        .options(joinedload(Receta.ingrediente))
        .filter(Receta.id_producto == datos.producto_id, Receta.id_ingrediente == datos.ingrediente_id)
        .first()
    )


@router.delete("/{producto_id}/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_receta(
    producto_id: int,
    ingrediente_id: int,
    db: Session = Depends(get_db),
    _=Depends(_escritura),
) -> None:
    receta = (
        db.query(Receta)
        .filter(Receta.id_producto == producto_id, Receta.id_ingrediente == ingrediente_id)
        .first()
    )
    if not receta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    db.delete(receta)
    db.commit()
```

- [ ] **Step 4: Correr los tests de nuevo**

Run: `cd api && python -m pytest app/tests/test_router_recetas.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Correr toda la suite de la API para evitar regresiones**

Run: `cd api && python -m pytest app/tests/ -v`
Expected: todos los tests existentes (15 previos + 5 nuevos de Tasks 1-2) PASS

- [ ] **Step 6: Agregar los requests de Postman**

En `postman/coffee-code.postman_collection.json`, dentro de `"03 - Cocina"`, insertar estos dos items justo después de `"Crear Receta (producto_ingrediente)"`:

```json
{
  "name": "Listar Receta de un Producto",
  "request": {
    "method": "GET",
    "auth": {
      "type": "bearer",
      "bearer": [
        {
          "key": "token",
          "value": "{{token_cocinero}}"
        }
      ]
    },
    "url": {
      "raw": "{{base_url}}/producto_ingrediente?producto_id={{producto_id}}",
      "host": [
        "{{base_url}}"
      ],
      "path": [
        "producto_ingrediente"
      ],
      "query": [
        {
          "key": "producto_id",
          "value": "{{producto_id}}"
        }
      ]
    }
  }
},
{
  "name": "Eliminar Ingrediente de Receta",
  "request": {
    "method": "DELETE",
    "auth": {
      "type": "bearer",
      "bearer": [
        {
          "key": "token",
          "value": "{{token_cocinero}}"
        }
      ]
    },
    "url": {
      "raw": "{{base_url}}/producto_ingrediente/{{producto_id}}/{{ingrediente_id}}",
      "host": [
        "{{base_url}}"
      ],
      "path": [
        "producto_ingrediente",
        "{{producto_id}}",
        "{{ingrediente_id}}"
      ]
    }
  }
},
```

- [ ] **Step 7: Commit**

```bash
git add api/app/routers/recetas.py api/app/tests/test_router_recetas.py postman/coffee-code.postman_collection.json
git commit -m "feat(api): agregar GET y DELETE para producto_ingrediente (recetas)"
```

---

## Parte B — Panel Web Admin (Flask)

### Task 3: Scaffold del proyecto Flask

**Files:**
- Create: `web-admin/requirements.txt`
- Create: `web-admin/Dockerfile`
- Create: `web-admin/.env.example`
- Create: `web-admin/.env`
- Create: `web-admin/wsgi.py`
- Create: `web-admin/app/__init__.py`
- Create: `web-admin/app/config.py`
- Modify: `docker-compose.yml`
- Test: `web-admin/tests/conftest.py`, `web-admin/tests/test_health.py`

**Interfaces:**
- Produces: `create_app(config_overrides: dict | None = None) -> Flask` en `web-admin/app/__init__.py` — factory usada por `wsgi.py` y por los tests. `Settings` en `web-admin/app/config.py` con atributos `secret_key: str`, `coffee_api_url: str`, `session_lifetime_hours: int`.

- [ ] **Step 1: Crear `requirements.txt`**

```
Flask==3.1.0
requests==2.32.3
python-dotenv==1.0.1
WeasyPrint==63.1
openpyxl==3.1.5
pytest==8.3.4
```

- [ ] **Step 2: Crear `.env.example` y `.env`**

`web-admin/.env.example`:

```
FLASK_SECRET_KEY=cambia-esta-llave-por-una-aleatoria-larga
COFFEE_API_URL=http://coffee_code_api:8000
SESSION_LIFETIME_HOURS=24
```

`web-admin/.env` (copia local para desarrollo, mismo patrón que `api/.env`):

```
FLASK_SECRET_KEY=dev-secret-key-cambia-en-produccion
COFFEE_API_URL=http://localhost:8010
SESSION_LIFETIME_HOURS=24
```

- [ ] **Step 3: Crear `app/config.py`**

```python
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    secret_key: str
    coffee_api_url: str
    session_lifetime_hours: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            secret_key=os.environ["FLASK_SECRET_KEY"],
            coffee_api_url=os.environ.get("COFFEE_API_URL", "http://localhost:8010"),
            session_lifetime_hours=int(os.environ.get("SESSION_LIFETIME_HOURS", "24")),
        )


settings = Settings.from_env()
```

- [ ] **Step 4: Crear la app factory `app/__init__.py`**

```python
from datetime import timedelta

from flask import Flask

from app.config import settings


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["COFFEE_API_URL"] = settings.coffee_api_url
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=settings.session_lifetime_hours)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    if config_overrides:
        app.config.update(config_overrides)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
```

- [ ] **Step 5: Crear `wsgi.py`**

```python
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

- [ ] **Step 6: Escribir el test de salud**

Crear `web-admin/tests/conftest.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app


@pytest.fixture()
def app():
    flask_app = create_app({"TESTING": True, "COFFEE_API_URL": "http://testserver"})
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()
```

Crear `web-admin/tests/test_health.py`:

```python
def test_health_endpoint(client):
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"status": "ok"}
```

- [ ] **Step 7: Correr el test**

Run: `cd web-admin && python -m pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 8: Crear el `Dockerfile`**

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "wsgi.py"]
```

(La lista de paquetes `libpango`/`libgdk-pixbuf` son las dependencias nativas que WeasyPrint necesita para renderizar PDF — sin ellas falla al importar.)

- [ ] **Step 9: Agregar el servicio a `docker-compose.yml`**

Modificar `docker-compose.yml`, agregar al final del bloque `services:` (después de `coffee_code_api`):

```yaml
  coffee_code_web:
    build: ./web-admin
    container_name: coffee_code_web
    restart: unless-stopped
    env_file:
      - ./web-admin/.env
    environment:
      COFFEE_API_URL: http://coffee_code_api:8000
    ports:
      - "8020:5000"
    depends_on:
      - coffee_code_api
    volumes:
      - ./web-admin:/app
```

- [ ] **Step 10: Levantar y verificar**

Run: `docker compose up -d --build coffee_code_web`
Run: `curl http://localhost:8020/health`
Expected: `{"status":"ok"}`

- [ ] **Step 11: Commit**

```bash
git add web-admin/requirements.txt web-admin/Dockerfile web-admin/.env.example web-admin/wsgi.py web-admin/app/__init__.py web-admin/app/config.py web-admin/tests/ docker-compose.yml
git commit -m "feat(web-admin): scaffold inicial de la app Flask"
```

Nota: `web-admin/.env` no se commitea si el repo ya ignora `.env` (verificar `.gitignore`; si `api/.env` está trackeado como excepción documentada, seguir el mismo criterio ya establecido en el repo).

---

### Task 4: `api_client.py` — cliente HTTP hacia la API central

**Files:**
- Create: `web-admin/app/api_client.py`
- Test: `web-admin/tests/test_api_client.py`

**Interfaces:**
- Consumes: `app.config.settings.coffee_api_url` (o el `base_url` inyectado en tests).
- Produces (contrato usado por todos los blueprints de las tareas siguientes):
  ```python
  class ApiError(Exception):
      status_code: int | None
      detail: str

  def login(base_url: str, correo: str, password: str) -> dict          # {"access_token": str, "rol": str}
  def listar_usuarios(base_url: str, token: str) -> list[dict]
  def crear_usuario(base_url: str, token: str, payload: dict) -> dict
  def actualizar_usuario(base_url: str, token: str, usuario_id: int, payload: dict) -> dict
  def listar_categorias(base_url: str, token: str) -> list[dict]
  def listar_productos(base_url: str, token: str) -> list[dict]
  def crear_producto(base_url: str, token: str, payload: dict) -> dict
  def actualizar_producto(base_url: str, token: str, producto_id: int, payload: dict) -> dict
  def eliminar_producto(base_url: str, token: str, producto_id: int) -> None
  def listar_ingredientes(base_url: str, token: str) -> list[dict]
  def crear_ingrediente(base_url: str, token: str, payload: dict) -> dict
  def ajustar_stock_ingrediente(base_url: str, token: str, ingrediente_id: int, cantidad: str) -> dict
  def listar_receta_producto(base_url: str, token: str, producto_id: int) -> list[dict]
  def crear_receta(base_url: str, token: str, payload: dict) -> dict
  def eliminar_receta(base_url: str, token: str, producto_id: int, ingrediente_id: int) -> None
  def obtener_reporte_admin(base_url: str, token: str, desde: str, hasta: str) -> dict
  ```

- [ ] **Step 1: Escribir el test primero**

Crear `web-admin/tests/test_api_client.py`:

```python
import pytest
import responses

from app.api_client import ApiError, listar_productos, login

BASE_URL = "http://testserver"


@responses.activate
def test_login_devuelve_token_y_rol():
    responses.add(
        responses.POST,
        f"{BASE_URL}/auth/login",
        json={"access_token": "abc123", "rol": "Administrador"},
        status=200,
    )

    resultado = login(BASE_URL, "admin@coffeecode.com", "Admin123!")

    assert resultado == {"access_token": "abc123", "rol": "Administrador"}


@responses.activate
def test_login_credenciales_invalidas_lanza_apierror():
    responses.add(
        responses.POST,
        f"{BASE_URL}/auth/login",
        json={"detail": "Correo o contraseña incorrectos"},
        status=401,
    )

    with pytest.raises(ApiError) as excinfo:
        login(BASE_URL, "malo@coffeecode.com", "mal")

    assert excinfo.value.status_code == 401
    assert "incorrectos" in excinfo.value.detail


@responses.activate
def test_listar_productos_envia_bearer_token():
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[{"id": 1, "nombre": "Latte"}],
        status=200,
    )

    resultado = listar_productos(BASE_URL, "token-de-prueba")

    assert resultado == [{"id": 1, "nombre": "Latte"}]
    assert responses.calls[0].request.headers["Authorization"] == "Bearer token-de-prueba"
```

Agregar `responses==0.25.3` a `web-admin/requirements.txt` (librería para mockear `requests` en tests, no se usa en producción).

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd web-admin && pip install -r requirements.txt && python -m pytest tests/test_api_client.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.api_client'`

- [ ] **Step 3: Implementar `app/api_client.py`**

```python
import requests

_TIMEOUT = 5


class ApiError(Exception):
    def __init__(self, status_code: int | None, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _headers(token: str | None) -> dict:
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _request(method: str, base_url: str, path: str, token: str | None = None, **kwargs):
    try:
        respuesta = requests.request(
            method, f"{base_url}{path}", headers=_headers(token), timeout=_TIMEOUT, **kwargs
        )
    except requests.RequestException as exc:
        raise ApiError(None, f"No se pudo conectar con la API: {exc}") from exc

    if respuesta.status_code >= 400:
        try:
            detalle = respuesta.json().get("detail", respuesta.text)
        except ValueError:
            detalle = respuesta.text
        raise ApiError(respuesta.status_code, detalle)

    if respuesta.status_code == 204 or not respuesta.content:
        return None
    return respuesta.json()


def login(base_url: str, correo: str, password: str) -> dict:
    return _request(
        "POST",
        base_url,
        "/auth/login",
        json={"correo_electronico": correo, "password": password},
    )


def listar_usuarios(base_url: str, token: str) -> list[dict]:
    return _request("GET", base_url, "/api/usuarios", token=token)


def crear_usuario(base_url: str, token: str, payload: dict) -> dict:
    return _request("POST", base_url, "/api/usuarios", token=token, json=payload)


def actualizar_usuario(base_url: str, token: str, usuario_id: int, payload: dict) -> dict:
    return _request("PUT", base_url, f"/api/usuarios/{usuario_id}", token=token, json=payload)


def listar_categorias(base_url: str, token: str) -> list[dict]:
    return _request("GET", base_url, "/categorias", token=token)


def listar_productos(base_url: str, token: str) -> list[dict]:
    return _request("GET", base_url, "/productos", token=token)


def crear_producto(base_url: str, token: str, payload: dict) -> dict:
    return _request("POST", base_url, "/productos", token=token, json=payload)


def actualizar_producto(base_url: str, token: str, producto_id: int, payload: dict) -> dict:
    return _request("PUT", base_url, f"/productos/{producto_id}", token=token, json=payload)


def eliminar_producto(base_url: str, token: str, producto_id: int) -> None:
    return _request("DELETE", base_url, f"/productos/{producto_id}", token=token)


def listar_ingredientes(base_url: str, token: str) -> list[dict]:
    return _request("GET", base_url, "/ingredientes", token=token)


def crear_ingrediente(base_url: str, token: str, payload: dict) -> dict:
    return _request("POST", base_url, "/ingredientes", token=token, json=payload)


def ajustar_stock_ingrediente(base_url: str, token: str, ingrediente_id: int, cantidad: str) -> dict:
    return _request(
        "PUT",
        base_url,
        f"/ingredientes/{ingrediente_id}/stock",
        token=token,
        json={"cantidad": cantidad},
    )


def listar_receta_producto(base_url: str, token: str, producto_id: int) -> list[dict]:
    return _request(
        "GET", base_url, "/producto_ingrediente", token=token, params={"producto_id": producto_id}
    )


def crear_receta(base_url: str, token: str, payload: dict) -> dict:
    return _request("POST", base_url, "/producto_ingrediente", token=token, json=payload)


def eliminar_receta(base_url: str, token: str, producto_id: int, ingrediente_id: int) -> None:
    return _request(
        "DELETE", base_url, f"/producto_ingrediente/{producto_id}/{ingrediente_id}", token=token
    )


def obtener_reporte_admin(base_url: str, token: str, desde: str, hasta: str) -> dict:
    return _request(
        "GET", base_url, "/api/reportes", token=token, params={"desde": desde, "hasta": hasta}
    )
```

- [ ] **Step 4: Correr los tests de nuevo**

Run: `cd web-admin && python -m pytest tests/test_api_client.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add web-admin/app/api_client.py web-admin/tests/test_api_client.py web-admin/requirements.txt
git commit -m "feat(web-admin): agregar cliente HTTP hacia la API central"
```

---

### Task 5: Autenticación, layout base y login

**Files:**
- Create: `web-admin/app/auth.py`
- Create: `web-admin/app/blueprints/__init__.py`
- Create: `web-admin/app/blueprints/auth.py`
- Create: `web-admin/app/templates/base.html`
- Create: `web-admin/app/templates/login.html`
- Create: `web-admin/app/templates/errors/401.html`
- Create: `web-admin/app/templates/errors/403.html`
- Create: `web-admin/app/static/css/theme.css`
- Create: `web-admin/app/static/js/charts-theme.js`
- Modify: `web-admin/app/__init__.py` (registrar blueprint, error handlers, `static_folder`/`template_folder` ya son default de Flask)
- Test: `web-admin/tests/test_auth.py`

**Interfaces:**
- Consumes: `api_client.login`, `api_client.ApiError` (Task 4).
- Produces:
  - `web-admin/app/auth.py`: `login_required(view)` decorador, `current_token() -> str | None`, `current_rol() -> str | None`.
  - Blueprint `auth` registrado con `url_prefix=""`, rutas `GET/POST /login`, `GET /logout`.
  - `base.html` con bloques Jinja `{% block title %}`, `{% block content %}`, `{% block scripts %}`, y variables de contexto disponibles en todas las vistas protegidas: `session["correo"]`.

- [ ] **Step 1: Escribir el test primero**

Crear `web-admin/tests/test_auth.py`:

```python
import responses

BASE_URL = "http://testserver"


def test_login_page_carga(client):
    respuesta = client.get("/login")
    assert respuesta.status_code == 200
    assert b"Coffee Code" in respuesta.data


@responses.activate
def test_login_exitoso_como_administrador_redirige_al_dashboard(client):
    responses.add(
        responses.POST,
        f"{BASE_URL}/auth/login",
        json={"access_token": "token-admin", "rol": "Administrador"},
        status=200,
    )

    respuesta = client.post(
        "/login",
        data={"correo": "admin@coffeecode.com", "password": "Admin123!"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    with client.session_transaction() as sess:
        assert sess["token"] == "token-admin"
        assert sess["rol"] == "Administrador"


@responses.activate
def test_login_con_rol_no_admin_es_rechazado(client):
    responses.add(
        responses.POST,
        f"{BASE_URL}/auth/login",
        json={"access_token": "token-mesero", "rol": "Mesero"},
        status=200,
    )

    respuesta = client.post(
        "/login",
        data={"correo": "mesero@coffeecode.com", "password": "Mesero123!"},
    )

    assert respuesta.status_code == 200
    assert "Administrador" in respuesta.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "token" not in sess


def test_ruta_protegida_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_logout_limpia_la_sesion(client):
    with client.session_transaction() as sess:
        sess["token"] = "algun-token"
        sess["rol"] = "Administrador"

    respuesta = client.get("/logout", follow_redirects=False)

    assert respuesta.status_code == 302
    with client.session_transaction() as sess:
        assert "token" not in sess
```

Nota: el test `test_ruta_protegida_sin_sesion_redirige_a_login` asume que `/` (dashboard) ya está protegida con `@login_required` — se registrará una ruta mínima placeholder en este task y el Task 11 la reemplaza con el dashboard real, manteniendo la protección.

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd web-admin && python -m pytest tests/test_auth.py -v`
Expected: FAIL (404 en `/login`, no existe el blueprint todavía)

- [ ] **Step 3: Implementar `app/auth.py`**

```python
from functools import wraps

from flask import current_app, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "token" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def current_token() -> str | None:
    return session.get("token")


def current_rol() -> str | None:
    return session.get("rol")


def api_base_url() -> str:
    return current_app.config["COFFEE_API_URL"]
```

- [ ] **Step 4: Implementar el blueprint de auth**

Crear `web-admin/app/blueprints/__init__.py` (vacío).

Crear `web-admin/app/blueprints/auth.py`:

```python
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.api_client import ApiError, login as api_login
from app.auth import api_base_url

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    correo = request.form.get("correo", "").strip()
    password = request.form.get("password", "")

    try:
        resultado = api_login(api_base_url(), correo, password)
    except ApiError as error:
        flash(error.detail, "error")
        return render_template("login.html")

    if resultado["rol"] != "Administrador":
        flash("Solo el rol Administrador puede acceder a este panel.", "error")
        return render_template("login.html")

    session.clear()
    session.permanent = True
    session["token"] = resultado["access_token"]
    session["rol"] = resultado["rol"]
    session["correo"] = correo

    return redirect(url_for("dashboard.index"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
```

- [ ] **Step 5: Crear las plantillas base**

Crear `web-admin/app/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Coffee Code Admin{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            espresso: '#3B2412',
            coffee: '#6F4E37',
            caramel: '#A87C5F',
            cream: '#F5E6D3',
          }
        }
      }
    }
  </script>
  <script src="https://unpkg.com/alpinejs@3.14.8/dist/cdn.min.js" defer></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"></script>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/theme.css') }}">
</head>
<body class="bg-cream text-espresso min-h-screen flex">
  {% if session.get('token') %}
  <aside class="w-64 bg-espresso text-cream flex flex-col shrink-0">
    <div class="px-6 py-5 border-b border-coffee/40">
      <span class="font-serif text-xl tracking-wide">Coffee Code</span>
      <div class="text-xs text-caramel">Panel Admin</div>
    </div>
    <nav class="flex-1 px-3 py-4 space-y-1 text-sm">
      <a href="{{ url_for('dashboard.index') }}" class="block px-3 py-2 rounded-lg hover:bg-coffee/40">Dashboard</a>
      <a href="{{ url_for('usuarios.listar') }}" class="block px-3 py-2 rounded-lg hover:bg-coffee/40">Usuarios</a>
      <a href="{{ url_for('productos.listar') }}" class="block px-3 py-2 rounded-lg hover:bg-coffee/40">Productos</a>
      <a href="{{ url_for('ingredientes.listar') }}" class="block px-3 py-2 rounded-lg hover:bg-coffee/40">Ingredientes</a>
      <a href="{{ url_for('recetas.listar') }}" class="block px-3 py-2 rounded-lg hover:bg-coffee/40">Recetas</a>
    </nav>
    <div class="px-6 py-4 border-t border-coffee/40 text-xs">
      <div class="truncate">{{ session.get('correo') }}</div>
      <a href="{{ url_for('auth.logout') }}" class="text-caramel hover:underline">Cerrar sesión</a>
    </div>
  </aside>
  {% endif %}
  <main class="flex-1 p-8">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="mb-6 space-y-2">
          {% for category, message in messages %}
            <div class="px-4 py-3 rounded-lg text-sm {{ 'bg-red-100 text-red-800' if category == 'error' else 'bg-green-100 text-green-800' }}">
              {{ message }}
            </div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>
  {% block scripts %}{% endblock %}
</body>
</html>
```

Crear `web-admin/app/templates/login.html`:

```html
{% extends "base.html" %}
{% block title %}Iniciar sesión — Coffee Code Admin{% endblock %}
{% block content %}
<div class="min-h-[80vh] flex items-center justify-center">
  <div class="w-full max-w-sm bg-white/70 backdrop-blur rounded-2xl shadow-xl p-8 border border-caramel/30">
    <h1 class="font-serif text-2xl text-espresso mb-1">Coffee Code</h1>
    <p class="text-sm text-coffee mb-6">Panel de Administración</p>
    <form method="post" class="space-y-4">
      <div>
        <label class="block text-sm font-medium mb-1" for="correo">Correo electrónico</label>
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-coffee" type="email" id="correo" name="correo" required>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1" for="password">Contraseña</label>
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-coffee" type="password" id="password" name="password" required>
      </div>
      <button type="submit" class="w-full bg-espresso text-cream rounded-lg py-2 font-medium hover:bg-coffee transition-colors">
        Entrar
      </button>
    </form>
  </div>
</div>
{% endblock %}
```

Crear `web-admin/app/templates/errors/401.html`:

```html
{% extends "base.html" %}
{% block title %}Sesión expirada{% endblock %}
{% block content %}
<div class="text-center mt-24">
  <h1 class="text-3xl font-serif mb-2">Tu sesión expiró</h1>
  <p class="text-coffee mb-6">Vuelve a iniciar sesión para continuar.</p>
  <a href="{{ url_for('auth.login') }}" class="inline-block bg-espresso text-cream px-5 py-2 rounded-lg">Ir a login</a>
</div>
{% endblock %}
```

Crear `web-admin/app/templates/errors/403.html`:

```html
{% extends "base.html" %}
{% block title %}Acceso no autorizado{% endblock %}
{% block content %}
<div class="text-center mt-24">
  <h1 class="text-3xl font-serif mb-2">No tienes permiso para esto</h1>
  <p class="text-coffee">Este panel es exclusivo para el rol Administrador.</p>
</div>
{% endblock %}
```

Crear `web-admin/app/static/css/theme.css`:

```css
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-thumb {
  background-color: #A87C5F;
  border-radius: 4px;
}
.card {
  background: white;
  border-radius: 1rem;
  box-shadow: 0 1px 3px rgba(59, 36, 18, 0.08), 0 1px 2px rgba(59, 36, 18, 0.06);
}
```

Crear `web-admin/app/static/js/charts-theme.js`:

```js
const coffeeChartPalette = {
  espresso: '#3B2412',
  coffee: '#6F4E37',
  caramel: '#A87C5F',
  cream: '#F5E6D3',
  positive: '#3E7C4A',
  negative: '#B4432D',
};

window.coffeeChartPalette = coffeeChartPalette;
```

- [ ] **Step 6: Registrar el blueprint y los error handlers en `app/__init__.py`**

Reemplazar el contenido de `web-admin/app/__init__.py`:

```python
from datetime import timedelta

from flask import Flask, redirect, render_template, url_for

from app.api_client import ApiError
from app.config import settings


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["COFFEE_API_URL"] = settings.coffee_api_url
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=settings.session_lifetime_hours)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    if config_overrides:
        app.config.update(config_overrides)

    from app.blueprints.auth import bp as auth_bp

    app.register_blueprint(auth_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def _placeholder_root():
        return redirect(url_for("auth.login"))

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        if error.status_code == 401:
            from flask import session

            session.clear()
            return render_template("errors/401.html"), 401
        if error.status_code == 403:
            return render_template("errors/403.html"), 403
        return render_template("errors/401.html", mensaje=error.detail), error.status_code or 500

    return app
```

(La ruta `_placeholder_root` en `/` se reemplaza en Task 11 por el blueprint `dashboard` — hasta entonces, el test `test_ruta_protegida_sin_sesion_redirige_a_login` seguirá pasando porque redirige a `/login`, aunque técnicamente aún no está detrás de `@login_required`; el Task 11 la vuelve a probar ya protegida.)

- [ ] **Step 7: Correr los tests de nuevo**

Run: `cd web-admin && python -m pytest tests/test_auth.py -v`
Expected: 5 tests PASS

- [ ] **Step 8: Commit**

```bash
git add web-admin/app/auth.py web-admin/app/blueprints/ web-admin/app/templates/ web-admin/app/static/ web-admin/app/__init__.py web-admin/tests/test_auth.py
git commit -m "feat(web-admin): login, sesion JWT y layout base"
```

---

### Task 6: Módulo Usuarios (CRUD + roles)

**Files:**
- Create: `web-admin/app/blueprints/usuarios.py`
- Create: `web-admin/app/templates/usuarios.html`
- Modify: `web-admin/app/__init__.py` (registrar blueprint, quitar `_placeholder_root` si Task 11 aún no corrió — dejar el placeholder hasta Task 11)
- Test: `web-admin/tests/test_usuarios.py`

**Interfaces:**
- Consumes: `api_client.listar_usuarios/crear_usuario/actualizar_usuario`, `app.auth.login_required/current_token/api_base_url`.
- Produces: blueprint `usuarios` con rutas `GET /usuarios` (`usuarios.listar`), `POST /usuarios/nuevo` (`usuarios.crear`), `POST /usuarios/<int:usuario_id>/editar` (`usuarios.editar`).

Los roles disponibles (`Mesero, Cajero, Cocinero, Administrador`) se muestran hardcodeados en el `<select>` del formulario — no hay endpoint `GET /roles` en la API y agregarlo está fuera de alcance (los 4 roles son fijos según el diccionario de datos de CLAUDE.md, no se crean dinámicamente).

- [ ] **Step 1: Escribir el test primero**

Crear `web-admin/tests/test_usuarios.py`:

```python
import responses

BASE_URL = "http://testserver"


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_listar_usuarios_muestra_tabla(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/usuarios",
        json=[
            {
                "id": 1,
                "nombre": "Ana",
                "apellido_paterno": "Ruiz",
                "apellido_materno": None,
                "correo_electronico": "ana@coffeecode.com",
                "activo": True,
                "fecha_creacion": "2026-01-01T00:00:00",
                "rol": {"id": 4, "nombre": "Administrador"},
            }
        ],
        status=200,
    )

    respuesta = client.get("/usuarios")

    assert respuesta.status_code == 200
    assert b"ana@coffeecode.com" in respuesta.data


@responses.activate
def test_crear_usuario_reenvia_payload_a_la_api(client):
    _login_como_admin(client)
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/usuarios",
        json={"id": 2},
        status=201,
    )

    respuesta = client.post(
        "/usuarios/nuevo",
        data={
            "nombre": "Luis",
            "apellido_paterno": "Perez",
            "apellido_materno": "",
            "correo_electronico": "luis@coffeecode.com",
            "password": "Password123",
            "id_rol": "1",
        },
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    enviado = responses.calls[-1].request
    assert enviado.headers["Authorization"] == "Bearer token-admin"


def test_usuarios_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/usuarios", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd web-admin && python -m pytest tests/test_usuarios.py -v`
Expected: FAIL (404, blueprint no existe)

- [ ] **Step 3: Implementar el blueprint**

Crear `web-admin/app/blueprints/usuarios.py`:

```python
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import ApiError, crear_usuario, actualizar_usuario, listar_usuarios
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

ROLES_DISPONIBLES = ["Mesero", "Cajero", "Cocinero", "Administrador"]
ROL_ID_POR_NOMBRE = {"Mesero": 1, "Cajero": 2, "Cocinero": 3, "Administrador": 4}


@bp.route("")
@login_required
def listar():
    usuarios = listar_usuarios(api_base_url(), current_token())
    return render_template("usuarios.html", usuarios=usuarios, roles=ROLES_DISPONIBLES)


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
    try:
        actualizar_usuario(api_base_url(), current_token(), usuario_id, payload)
        flash("Usuario actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar el usuario: {error.detail}", "error")
    return redirect(url_for("usuarios.listar"))
```

Nota: el `id_rol` del formulario de creación se envía como el valor seleccionado en el `<select>` del template (Step 4), poblado dinámicamente con los IDs reales que trae cada usuario en `usuario.rol.id` cuando existen datos, y con `ROL_ID_POR_NOMBRE` como *fallback* fijo (los 4 roles se siembran una sola vez en `app/seed.py` de la API con esos IDs consecutivos 1-4, ver `api/app/seed.py`).

- [ ] **Step 4: Crear la plantilla**

Crear `web-admin/app/templates/usuarios.html`:

```html
{% extends "base.html" %}
{% block title %}Usuarios — Coffee Code Admin{% endblock %}
{% block content %}
<div x-data="{ modalAbierto: false, editando: null }">
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-serif">Usuarios y roles</h1>
    <button @click="modalAbierto = true; editando = null" class="bg-espresso text-cream px-4 py-2 rounded-lg hover:bg-coffee">
      + Nuevo usuario
    </button>
  </div>

  <div class="card overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-espresso/5 text-left text-xs uppercase tracking-wide text-coffee">
        <tr>
          <th class="px-4 py-3">Nombre</th>
          <th class="px-4 py-3">Correo</th>
          <th class="px-4 py-3">Rol</th>
          <th class="px-4 py-3">Estado</th>
          <th class="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody>
        {% for usuario in usuarios %}
        <tr class="border-t border-caramel/20 hover:bg-cream/60">
          <td class="px-4 py-3">{{ usuario.nombre }} {{ usuario.apellido_paterno }}</td>
          <td class="px-4 py-3">{{ usuario.correo_electronico }}</td>
          <td class="px-4 py-3">
            <span class="px-2 py-1 rounded-full bg-caramel/20 text-espresso text-xs">{{ usuario.rol.nombre }}</span>
          </td>
          <td class="px-4 py-3">
            {% if usuario.activo %}
              <span class="text-green-700">Activo</span>
            {% else %}
              <span class="text-red-700">Inactivo</span>
            {% endif %}
          </td>
          <td class="px-4 py-3 text-right">
            <button
              @click="modalAbierto = true; editando = {{ {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'apellido_paterno': usuario.apellido_paterno,
                'apellido_materno': usuario.apellido_materno or '',
                'correo_electronico': usuario.correo_electronico,
                'id_rol': usuario.rol.id,
                'activo': usuario.activo,
              } | tojson }}"
              class="text-coffee hover:underline">Editar</button>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div x-show="modalAbierto" x-cloak class="fixed inset-0 bg-espresso/50 flex items-center justify-center z-50">
    <div class="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md" @click.outside="modalAbierto = false">
      <h2 class="text-lg font-serif mb-4" x-text="editando ? 'Editar usuario' : 'Nuevo usuario'"></h2>
      <form :action="editando ? `/usuarios/${editando.id}/editar` : '/usuarios/nuevo'" method="post" class="space-y-3">
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" name="nombre" placeholder="Nombre" :value="editando ? editando.nombre : ''" required>
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" name="apellido_paterno" placeholder="Apellido paterno" :value="editando ? editando.apellido_paterno : ''" required>
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" name="apellido_materno" placeholder="Apellido materno (opcional)" :value="editando ? editando.apellido_materno : ''">
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" type="email" name="correo_electronico" placeholder="Correo electrónico" :value="editando ? editando.correo_electronico : ''" required>
        <template x-if="!editando">
          <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" type="password" name="password" placeholder="Contraseña" required>
        </template>
        <select class="w-full rounded-lg border border-caramel/40 px-3 py-2" name="id_rol" required>
          {% for rol in roles %}
          <option value="{{ loop.index }}" x-bind:selected="editando && editando.id_rol === {{ loop.index }}">{{ rol }}</option>
          {% endfor %}
        </select>
        <template x-if="editando">
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" name="activo" :checked="editando && editando.activo"> Usuario activo
          </label>
        </template>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="modalAbierto = false" class="px-4 py-2 rounded-lg border border-caramel/40">Cancelar</button>
          <button type="submit" class="px-4 py-2 rounded-lg bg-espresso text-cream hover:bg-coffee">Guardar</button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Registrar el blueprint en `app/__init__.py`**

Agregar junto al registro de `auth_bp`:

```python
    from app.blueprints.usuarios import bp as usuarios_bp

    app.register_blueprint(usuarios_bp)
```

- [ ] **Step 6: Correr los tests de nuevo**

Run: `cd web-admin && python -m pytest tests/test_usuarios.py -v`
Expected: 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add web-admin/app/blueprints/usuarios.py web-admin/app/templates/usuarios.html web-admin/app/__init__.py web-admin/tests/test_usuarios.py
git commit -m "feat(web-admin): modulo de usuarios y roles"
```

---

### Task 7: Módulo Productos (+ categorías)

**Files:**
- Create: `web-admin/app/blueprints/productos.py`
- Create: `web-admin/app/templates/productos.html`
- Modify: `web-admin/app/__init__.py`
- Test: `web-admin/tests/test_productos.py`

**Interfaces:**
- Consumes: `api_client.listar_productos/crear_producto/actualizar_producto/eliminar_producto/listar_categorias`.
- Produces: blueprint `productos`, rutas `GET /productos` (`productos.listar`), `POST /productos/nuevo` (`productos.crear`), `POST /productos/<int:producto_id>/editar` (`productos.editar`), `POST /productos/<int:producto_id>/eliminar` (`productos.eliminar`).

- [ ] **Step 1: Escribir el test primero**

Crear `web-admin/tests/test_productos.py`:

```python
import responses

BASE_URL = "http://testserver"


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_listar_productos_muestra_categoria(client):
    _login_como_admin(client)
    responses.add(responses.GET, f"{BASE_URL}/categorias", json=[{"id": 1, "nombre": "Bebidas calientes"}], status=200)
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[
            {
                "id": 1,
                "nombre": "Latte",
                "descripcion": None,
                "precio_venta": "55.00",
                "disponible": True,
                "activo": True,
                "categoria": {"id": 1, "nombre": "Bebidas calientes"},
            }
        ],
        status=200,
    )

    respuesta = client.get("/productos")

    assert respuesta.status_code == 200
    assert b"Latte" in respuesta.data
    assert b"Bebidas calientes" in respuesta.data


@responses.activate
def test_eliminar_producto_hace_soft_delete(client):
    _login_como_admin(client)
    responses.add(responses.DELETE, f"{BASE_URL}/productos/1", status=204)

    respuesta = client.post("/productos/1/eliminar", follow_redirects=False)

    assert respuesta.status_code == 302
    assert responses.calls[-1].request.method == "DELETE"
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd web-admin && python -m pytest tests/test_productos.py -v`
Expected: FAIL (404)

- [ ] **Step 3: Implementar el blueprint**

Crear `web-admin/app/blueprints/productos.py`:

```python
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import (
    ApiError,
    actualizar_producto,
    crear_producto,
    eliminar_producto,
    listar_categorias,
    listar_productos,
)
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("productos", __name__, url_prefix="/productos")


@bp.route("")
@login_required
def listar():
    token = current_token()
    base_url = api_base_url()
    productos = listar_productos(base_url, token)
    categorias = listar_categorias(base_url, token)
    return render_template("productos.html", productos=productos, categorias=categorias)


def _payload_desde_formulario() -> dict:
    return {
        "nombre": request.form["nombre"],
        "descripcion": request.form.get("descripcion") or None,
        "precio_venta": request.form["precio_venta"],
        "disponible": request.form.get("disponible") == "on",
        "activo": request.form.get("activo") == "on",
        "id_categoria": int(request.form["id_categoria"]),
    }


@bp.route("/nuevo", methods=["POST"])
@login_required
def crear():
    try:
        crear_producto(api_base_url(), current_token(), _payload_desde_formulario())
        flash("Producto creado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo crear el producto: {error.detail}", "error")
    return redirect(url_for("productos.listar"))


@bp.route("/<int:producto_id>/editar", methods=["POST"])
@login_required
def editar(producto_id: int):
    try:
        actualizar_producto(api_base_url(), current_token(), producto_id, _payload_desde_formulario())
        flash("Producto actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo actualizar el producto: {error.detail}", "error")
    return redirect(url_for("productos.listar"))


@bp.route("/<int:producto_id>/eliminar", methods=["POST"])
@login_required
def eliminar(producto_id: int):
    try:
        eliminar_producto(api_base_url(), current_token(), producto_id)
        flash("Producto desactivado.", "success")
    except ApiError as error:
        flash(f"No se pudo desactivar el producto: {error.detail}", "error")
    return redirect(url_for("productos.listar"))
```

- [ ] **Step 4: Crear la plantilla**

Crear `web-admin/app/templates/productos.html`:

```html
{% extends "base.html" %}
{% block title %}Productos — Coffee Code Admin{% endblock %}
{% block content %}
<div x-data="{ modalAbierto: false, editando: null }">
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-serif">Catálogo de productos</h1>
    <button @click="modalAbierto = true; editando = null" class="bg-espresso text-cream px-4 py-2 rounded-lg hover:bg-coffee">
      + Nuevo producto
    </button>
  </div>

  <div class="card overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-espresso/5 text-left text-xs uppercase tracking-wide text-coffee">
        <tr>
          <th class="px-4 py-3">Nombre</th>
          <th class="px-4 py-3">Categoría</th>
          <th class="px-4 py-3">Precio</th>
          <th class="px-4 py-3">Disponible</th>
          <th class="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody>
        {% for producto in productos %}
        <tr class="border-t border-caramel/20 hover:bg-cream/60">
          <td class="px-4 py-3">{{ producto.nombre }}</td>
          <td class="px-4 py-3">{{ producto.categoria.nombre }}</td>
          <td class="px-4 py-3">${{ "%.2f"|format(producto.precio_venta|float) }}</td>
          <td class="px-4 py-3">
            {% if producto.disponible %}<span class="text-green-700">Sí</span>{% else %}<span class="text-red-700">No</span>{% endif %}
          </td>
          <td class="px-4 py-3 text-right space-x-3">
            <button
              @click="modalAbierto = true; editando = {{ {
                'id': producto.id,
                'nombre': producto.nombre,
                'descripcion': producto.descripcion or '',
                'precio_venta': producto.precio_venta,
                'disponible': producto.disponible,
                'activo': producto.activo,
                'id_categoria': producto.categoria.id,
              } | tojson }}"
              class="text-coffee hover:underline">Editar</button>
            <form action="{{ url_for('productos.eliminar', producto_id=producto.id) }}" method="post" class="inline" onsubmit="return confirm('¿Desactivar este producto?');">
              <button type="submit" class="text-red-700 hover:underline">Desactivar</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div x-show="modalAbierto" x-cloak class="fixed inset-0 bg-espresso/50 flex items-center justify-center z-50">
    <div class="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md" @click.outside="modalAbierto = false">
      <h2 class="text-lg font-serif mb-4" x-text="editando ? 'Editar producto' : 'Nuevo producto'"></h2>
      <form :action="editando ? `/productos/${editando.id}/editar` : '/productos/nuevo'" method="post" class="space-y-3">
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" name="nombre" placeholder="Nombre" :value="editando ? editando.nombre : ''" required>
        <textarea class="w-full rounded-lg border border-caramel/40 px-3 py-2" name="descripcion" placeholder="Descripción (opcional)" x-text="editando ? editando.descripcion : ''"></textarea>
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" type="number" step="0.01" min="0.01" name="precio_venta" placeholder="Precio de venta" :value="editando ? editando.precio_venta : ''" required>
        <select class="w-full rounded-lg border border-caramel/40 px-3 py-2" name="id_categoria" required>
          {% for categoria in categorias %}
          <option value="{{ categoria.id }}">{{ categoria.nombre }}</option>
          {% endfor %}
        </select>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" name="disponible" :checked="!editando || editando.disponible" checked> Disponible
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" name="activo" :checked="!editando || editando.activo" checked> Activo
        </label>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="modalAbierto = false" class="px-4 py-2 rounded-lg border border-caramel/40">Cancelar</button>
          <button type="submit" class="px-4 py-2 rounded-lg bg-espresso text-cream hover:bg-coffee">Guardar</button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Registrar el blueprint**

En `web-admin/app/__init__.py`, agregar:

```python
    from app.blueprints.productos import bp as productos_bp

    app.register_blueprint(productos_bp)
```

- [ ] **Step 6: Correr los tests**

Run: `cd web-admin && python -m pytest tests/test_productos.py -v`
Expected: 2 tests PASS

- [ ] **Step 7: Commit**

```bash
git add web-admin/app/blueprints/productos.py web-admin/app/templates/productos.html web-admin/app/__init__.py web-admin/tests/test_productos.py
git commit -m "feat(web-admin): modulo de productos y categorias"
```

---

### Task 8: Módulo Ingredientes (+ ajuste de stock)

**Files:**
- Create: `web-admin/app/blueprints/ingredientes.py`
- Create: `web-admin/app/templates/ingredientes.html`
- Modify: `web-admin/app/__init__.py`
- Test: `web-admin/tests/test_ingredientes.py`

**Interfaces:**
- Consumes: `api_client.listar_ingredientes/crear_ingrediente/ajustar_stock_ingrediente`.
- Produces: blueprint `ingredientes`, rutas `GET /ingredientes` (`ingredientes.listar`), `POST /ingredientes/nuevo` (`ingredientes.crear`), `POST /ingredientes/<int:ingrediente_id>/ajustar-stock` (`ingredientes.ajustar_stock`).

- [ ] **Step 1: Escribir el test primero**

Crear `web-admin/tests/test_ingredientes.py`:

```python
import responses

BASE_URL = "http://testserver"


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_listar_ingredientes_marca_stock_bajo(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/ingredientes",
        json=[
            {
                "id": 1,
                "nombre": "Leche entera",
                "unidad": "ml",
                "stock_actual": "500.00",
                "stock_minimo": "1000.00",
                "costo_unitario": "0.02",
                "activo": True,
            }
        ],
        status=200,
    )

    respuesta = client.get("/ingredientes")

    assert respuesta.status_code == 200
    assert b"Leche entera" in respuesta.data
    assert b"Stock bajo" in respuesta.data


@responses.activate
def test_ajustar_stock_envia_delta_a_la_api(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/ingredientes/1/stock",
        json={"id": 1, "stock_actual": "1500.00"},
        status=200,
    )

    respuesta = client.post(
        "/ingredientes/1/ajustar-stock",
        data={"cantidad": "1000"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    import json

    cuerpo_enviado = json.loads(responses.calls[-1].request.body)
    assert cuerpo_enviado == {"cantidad": "1000"}
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd web-admin && python -m pytest tests/test_ingredientes.py -v`
Expected: FAIL (404)

- [ ] **Step 3: Implementar el blueprint**

Crear `web-admin/app/blueprints/ingredientes.py`:

```python
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import ApiError, ajustar_stock_ingrediente, crear_ingrediente, listar_ingredientes
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("ingredientes", __name__, url_prefix="/ingredientes")


@bp.route("")
@login_required
def listar():
    ingredientes = listar_ingredientes(api_base_url(), current_token())
    return render_template("ingredientes.html", ingredientes=ingredientes)


@bp.route("/nuevo", methods=["POST"])
@login_required
def crear():
    payload = {
        "nombre": request.form["nombre"],
        "unidad": request.form["unidad"],
        "stock_actual": request.form.get("stock_actual") or "0",
        "stock_minimo": request.form["stock_minimo"],
        "costo_unitario": request.form["costo_unitario"],
        "activo": True,
    }
    try:
        crear_ingrediente(api_base_url(), current_token(), payload)
        flash("Ingrediente creado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo crear el ingrediente: {error.detail}", "error")
    return redirect(url_for("ingredientes.listar"))


@bp.route("/<int:ingrediente_id>/ajustar-stock", methods=["POST"])
@login_required
def ajustar_stock(ingrediente_id: int):
    cantidad = request.form["cantidad"]
    try:
        ajustar_stock_ingrediente(api_base_url(), current_token(), ingrediente_id, cantidad)
        flash("Stock actualizado correctamente.", "success")
    except ApiError as error:
        flash(f"No se pudo ajustar el stock: {error.detail}", "error")
    return redirect(url_for("ingredientes.listar"))
```

- [ ] **Step 4: Crear la plantilla**

Crear `web-admin/app/templates/ingredientes.html`:

```html
{% extends "base.html" %}
{% block title %}Ingredientes — Coffee Code Admin{% endblock %}
{% block content %}
<div x-data="{ modalAbierto: false, modalStock: null }">
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-serif">Inventario de ingredientes</h1>
    <button @click="modalAbierto = true" class="bg-espresso text-cream px-4 py-2 rounded-lg hover:bg-coffee">
      + Nuevo ingrediente
    </button>
  </div>

  <div class="card overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-espresso/5 text-left text-xs uppercase tracking-wide text-coffee">
        <tr>
          <th class="px-4 py-3">Nombre</th>
          <th class="px-4 py-3">Stock actual</th>
          <th class="px-4 py-3">Stock mínimo</th>
          <th class="px-4 py-3">Costo unitario</th>
          <th class="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody>
        {% for ingrediente in ingredientes %}
        {% set bajo = ingrediente.stock_actual|float < ingrediente.stock_minimo|float %}
        <tr class="border-t border-caramel/20 hover:bg-cream/60 {{ 'bg-red-50' if bajo }}">
          <td class="px-4 py-3">
            {{ ingrediente.nombre }}
            {% if bajo %}<span class="ml-2 text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-800">Stock bajo</span>{% endif %}
          </td>
          <td class="px-4 py-3">{{ ingrediente.stock_actual }} {{ ingrediente.unidad }}</td>
          <td class="px-4 py-3">{{ ingrediente.stock_minimo }} {{ ingrediente.unidad }}</td>
          <td class="px-4 py-3">${{ "%.2f"|format(ingrediente.costo_unitario|float) }}</td>
          <td class="px-4 py-3 text-right">
            <button @click="modalStock = {{ {'id': ingrediente.id, 'nombre': ingrediente.nombre} | tojson }}" class="text-coffee hover:underline">Ajustar stock</button>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div x-show="modalAbierto" x-cloak class="fixed inset-0 bg-espresso/50 flex items-center justify-center z-50">
    <div class="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md" @click.outside="modalAbierto = false">
      <h2 class="text-lg font-serif mb-4">Nuevo ingrediente</h2>
      <form action="{{ url_for('ingredientes.crear') }}" method="post" class="space-y-3">
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" name="nombre" placeholder="Nombre" required>
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" name="unidad" placeholder="Unidad (ml, g, pza)" required>
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" type="number" step="0.01" min="0" name="stock_actual" placeholder="Stock inicial">
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" type="number" step="0.01" min="0" name="stock_minimo" placeholder="Stock mínimo" required>
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" type="number" step="0.01" min="0.01" name="costo_unitario" placeholder="Costo unitario" required>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="modalAbierto = false" class="px-4 py-2 rounded-lg border border-caramel/40">Cancelar</button>
          <button type="submit" class="px-4 py-2 rounded-lg bg-espresso text-cream hover:bg-coffee">Guardar</button>
        </div>
      </form>
    </div>
  </div>

  <div x-show="modalStock" x-cloak class="fixed inset-0 bg-espresso/50 flex items-center justify-center z-50">
    <div class="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm" @click.outside="modalStock = null">
      <h2 class="text-lg font-serif mb-4">Ajustar stock — <span x-text="modalStock && modalStock.nombre"></span></h2>
      <form :action="modalStock ? `/ingredientes/${modalStock.id}/ajustar-stock` : '#'" method="post" class="space-y-3">
        <label class="block text-sm text-coffee">Cantidad a sumar (usa negativo para restar)</label>
        <input class="w-full rounded-lg border border-caramel/40 px-3 py-2" type="number" step="0.01" name="cantidad" required>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="modalStock = null" class="px-4 py-2 rounded-lg border border-caramel/40">Cancelar</button>
          <button type="submit" class="px-4 py-2 rounded-lg bg-espresso text-cream hover:bg-coffee">Aplicar</button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Registrar el blueprint**

En `web-admin/app/__init__.py`:

```python
    from app.blueprints.ingredientes import bp as ingredientes_bp

    app.register_blueprint(ingredientes_bp)
```

- [ ] **Step 6: Correr los tests**

Run: `cd web-admin && python -m pytest tests/test_ingredientes.py -v`
Expected: 2 tests PASS

- [ ] **Step 7: Commit**

```bash
git add web-admin/app/blueprints/ingredientes.py web-admin/app/templates/ingredientes.html web-admin/app/__init__.py web-admin/tests/test_ingredientes.py
git commit -m "feat(web-admin): modulo de ingredientes e inventario"
```

---

### Task 9: Módulo Recetas

**Files:**
- Create: `web-admin/app/blueprints/recetas.py`
- Create: `web-admin/app/templates/recetas.html`
- Modify: `web-admin/app/__init__.py`
- Test: `web-admin/tests/test_recetas.py`

**Interfaces:**
- Consumes: `api_client.listar_productos`, `api_client.listar_ingredientes`, `api_client.listar_receta_producto`, `api_client.crear_receta`, `api_client.eliminar_receta` (todas de Task 4, `listar_receta_producto`/`eliminar_receta` habilitadas por Task 2 de la API).
- Produces: blueprint `recetas`, rutas `GET /recetas` (`recetas.listar`, lista de productos), `GET /recetas/<int:producto_id>` (`recetas.detalle`, receta de un producto), `POST /recetas/<int:producto_id>/agregar` (`recetas.agregar`), `POST /recetas/<int:producto_id>/<int:ingrediente_id>/eliminar` (`recetas.eliminar`).

- [ ] **Step 1: Escribir el test primero**

Crear `web-admin/tests/test_recetas.py`:

```python
import responses

BASE_URL = "http://testserver"


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_listar_recetas_muestra_productos(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[{"id": 1, "nombre": "Latte", "categoria": {"id": 1, "nombre": "Bebidas calientes"}}],
        status=200,
    )

    respuesta = client.get("/recetas")

    assert respuesta.status_code == 200
    assert b"Latte" in respuesta.data


@responses.activate
def test_detalle_receta_muestra_ingredientes(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[{"id": 1, "nombre": "Latte", "categoria": {"id": 1, "nombre": "Bebidas calientes"}}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/producto_ingrediente",
        json=[
            {
                "id_producto": 1,
                "id_ingrediente": 2,
                "cantidad_requerida": "200.00",
                "ingrediente": {"id": 2, "nombre": "Leche entera", "unidad": "ml"},
            }
        ],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/ingredientes",
        json=[
            {
                "id": 2,
                "nombre": "Leche entera",
                "unidad": "ml",
                "stock_actual": "5000",
                "stock_minimo": "1000",
                "costo_unitario": "0.02",
                "activo": True,
            }
        ],
        status=200,
    )

    respuesta = client.get("/recetas/1")

    assert respuesta.status_code == 200
    assert b"Leche entera" in respuesta.data


@responses.activate
def test_eliminar_ingrediente_de_receta(client):
    _login_como_admin(client)
    responses.add(responses.DELETE, f"{BASE_URL}/producto_ingrediente/1/2", status=204)

    respuesta = client.post("/recetas/1/2/eliminar", follow_redirects=False)

    assert respuesta.status_code == 302
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd web-admin && python -m pytest tests/test_recetas.py -v`
Expected: FAIL (404)

- [ ] **Step 3: Implementar el blueprint**

Crear `web-admin/app/blueprints/recetas.py`:

```python
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.api_client import (
    ApiError,
    crear_receta,
    eliminar_receta,
    listar_ingredientes,
    listar_productos,
    listar_receta_producto,
)
from app.auth import api_base_url, current_token, login_required

bp = Blueprint("recetas", __name__, url_prefix="/recetas")


@bp.route("")
@login_required
def listar():
    productos = listar_productos(api_base_url(), current_token())
    return render_template("recetas.html", productos=productos, producto_seleccionado=None, receta=None, ingredientes=None)


@bp.route("/<int:producto_id>")
@login_required
def detalle(producto_id: int):
    token = current_token()
    base_url = api_base_url()
    productos = listar_productos(base_url, token)
    producto_seleccionado = next((p for p in productos if p["id"] == producto_id), None)
    receta = listar_receta_producto(base_url, token, producto_id)
    ingredientes = listar_ingredientes(base_url, token)
    return render_template(
        "recetas.html",
        productos=productos,
        producto_seleccionado=producto_seleccionado,
        receta=receta,
        ingredientes=ingredientes,
    )


@bp.route("/<int:producto_id>/agregar", methods=["POST"])
@login_required
def agregar(producto_id: int):
    payload = {
        "producto_id": producto_id,
        "ingrediente_id": int(request.form["ingrediente_id"]),
        "cantidad": request.form["cantidad"],
    }
    try:
        crear_receta(api_base_url(), current_token(), payload)
        flash("Ingrediente agregado a la receta.", "success")
    except ApiError as error:
        flash(f"No se pudo agregar el ingrediente: {error.detail}", "error")
    return redirect(url_for("recetas.detalle", producto_id=producto_id))


@bp.route("/<int:producto_id>/<int:ingrediente_id>/eliminar", methods=["POST"])
@login_required
def eliminar(producto_id: int, ingrediente_id: int):
    try:
        eliminar_receta(api_base_url(), current_token(), producto_id, ingrediente_id)
        flash("Ingrediente quitado de la receta.", "success")
    except ApiError as error:
        flash(f"No se pudo quitar el ingrediente: {error.detail}", "error")
    return redirect(url_for("recetas.detalle", producto_id=producto_id))
```

- [ ] **Step 4: Crear la plantilla**

Crear `web-admin/app/templates/recetas.html`:

```html
{% extends "base.html" %}
{% block title %}Recetas — Coffee Code Admin{% endblock %}
{% block content %}
<div class="grid grid-cols-3 gap-6">
  <div class="card p-4 col-span-1">
    <h2 class="font-serif text-lg mb-3">Productos</h2>
    <ul class="space-y-1 text-sm">
      {% for producto in productos %}
      <li>
        <a href="{{ url_for('recetas.detalle', producto_id=producto.id) }}"
           class="block px-3 py-2 rounded-lg {{ 'bg-coffee text-cream' if producto_seleccionado and producto_seleccionado.id == producto.id else 'hover:bg-cream' }}">
          {{ producto.nombre }}
        </a>
      </li>
      {% endfor %}
    </ul>
  </div>

  <div class="card p-4 col-span-2">
    {% if producto_seleccionado %}
    <h2 class="font-serif text-lg mb-3">Receta de {{ producto_seleccionado.nombre }}</h2>
    <table class="w-full text-sm mb-6">
      <thead class="text-left text-xs uppercase tracking-wide text-coffee">
        <tr>
          <th class="py-2">Ingrediente</th>
          <th class="py-2">Cantidad requerida</th>
          <th class="py-2"></th>
        </tr>
      </thead>
      <tbody>
        {% for item in receta %}
        <tr class="border-t border-caramel/20">
          <td class="py-2">{{ item.ingrediente.nombre }}</td>
          <td class="py-2">{{ item.cantidad_requerida }} {{ item.ingrediente.unidad }}</td>
          <td class="py-2 text-right">
            <form action="{{ url_for('recetas.eliminar', producto_id=producto_seleccionado.id, ingrediente_id=item.id_ingrediente) }}" method="post" onsubmit="return confirm('¿Quitar este ingrediente de la receta?');">
              <button type="submit" class="text-red-700 hover:underline">Quitar</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <h3 class="font-serif text-base mb-2">Agregar ingrediente</h3>
    <form action="{{ url_for('recetas.agregar', producto_id=producto_seleccionado.id) }}" method="post" class="flex gap-2">
      <select name="ingrediente_id" class="flex-1 rounded-lg border border-caramel/40 px-3 py-2" required>
        {% for ingrediente in ingredientes %}
        <option value="{{ ingrediente.id }}">{{ ingrediente.nombre }} ({{ ingrediente.unidad }})</option>
        {% endfor %}
      </select>
      <input type="number" step="0.01" min="0.01" name="cantidad" placeholder="Cantidad" class="w-32 rounded-lg border border-caramel/40 px-3 py-2" required>
      <button type="submit" class="bg-espresso text-cream px-4 py-2 rounded-lg hover:bg-coffee">Agregar</button>
    </form>
    {% else %}
    <p class="text-coffee">Selecciona un producto para ver o editar su receta.</p>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Registrar el blueprint**

En `web-admin/app/__init__.py`:

```python
    from app.blueprints.recetas import bp as recetas_bp

    app.register_blueprint(recetas_bp)
```

- [ ] **Step 6: Correr los tests**

Run: `cd web-admin && python -m pytest tests/test_recetas.py -v`
Expected: 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add web-admin/app/blueprints/recetas.py web-admin/app/templates/recetas.html web-admin/app/__init__.py web-admin/tests/test_recetas.py
git commit -m "feat(web-admin): modulo de recetas"
```

---

### Task 10: Cálculos de reportes accionables (lógica pura)

Este es el módulo más importante para el requisito de "reportes sólidos": vive separado de Flask (funciones puras que reciben datos ya obtenidos de la API) para poder probarse sin mocks de HTTP.

**Files:**
- Create: `web-admin/app/reportes.py`
- Test: `web-admin/tests/test_reportes.py`

**Interfaces:**
- Produces:
  ```python
  def periodo_anterior(desde: date, hasta: date) -> tuple[date, date]
  def calcular_margen_pct(total_ventas: Decimal, ganancia_neta: Decimal) -> Decimal
  def variacion_pct(actual: Decimal, anterior: Decimal) -> Decimal | None
  def costo_receta(receta: list[dict]) -> Decimal
  def ranking_margen(top_productos: list[dict], costos_por_producto: dict[int, Decimal]) -> list[dict]
  def riesgo_inventario(ingredientes: list[dict], mapa_ingrediente_a_productos: dict[int, list[str]]) -> list[dict]
  def mapa_ingrediente_a_productos(recetas_por_producto: dict[int, list[dict]], productos_por_id: dict[int, dict]) -> dict[int, list[str]]
  ```

- [ ] **Step 1: Escribir los tests primero**

Crear `web-admin/tests/test_reportes.py`:

```python
from datetime import date
from decimal import Decimal

from app.reportes import (
    calcular_margen_pct,
    costo_receta,
    mapa_ingrediente_a_productos,
    periodo_anterior,
    ranking_margen,
    riesgo_inventario,
    variacion_pct,
)


def test_periodo_anterior_mismo_numero_de_dias():
    desde = date(2026, 6, 1)
    hasta = date(2026, 6, 10)

    desde_prev, hasta_prev = periodo_anterior(desde, hasta)

    assert hasta_prev == desde
    assert (hasta - desde) == (hasta_prev - desde_prev)
    assert desde_prev == date(2026, 5, 23)


def test_calcular_margen_pct():
    resultado = calcular_margen_pct(Decimal("1000"), Decimal("250"))
    assert resultado == Decimal("25.00")


def test_calcular_margen_pct_con_ventas_cero():
    resultado = calcular_margen_pct(Decimal("0"), Decimal("0"))
    assert resultado == Decimal("0")


def test_variacion_pct_positiva():
    resultado = variacion_pct(Decimal("120"), Decimal("100"))
    assert resultado == Decimal("20.00")


def test_variacion_pct_sin_periodo_anterior():
    resultado = variacion_pct(Decimal("120"), Decimal("0"))
    assert resultado is None


def test_costo_receta_suma_cantidad_por_costo_unitario():
    receta = [
        {"cantidad_requerida": "200.00", "ingrediente": {"costo_unitario": "0.02"}},
        {"cantidad_requerida": "10.00", "ingrediente": {"costo_unitario": "1.50"}},
    ]
    assert costo_receta(receta) == Decimal("19.00")


def test_ranking_margen_ordena_de_menor_a_mayor_margen_pct():
    top_productos = [
        {"producto_id": 1, "nombre": "Latte", "ingresos": "550.00", "cantidad_vendida": 10},
        {"producto_id": 2, "nombre": "Espresso", "ingresos": "300.00", "cantidad_vendida": 10},
    ]
    costos = {1: Decimal("40.00"), 2: Decimal("5.00")}

    resultado = ranking_margen(top_productos, costos)

    assert resultado[0]["producto_id"] == 1
    assert resultado[0]["margen_pct"] < resultado[1]["margen_pct"]


def test_mapa_ingrediente_a_productos():
    recetas_por_producto = {
        1: [{"id_ingrediente": 9, "ingrediente": {"nombre": "Leche"}}],
        2: [{"id_ingrediente": 9, "ingrediente": {"nombre": "Leche"}}],
    }
    productos_por_id = {1: {"nombre": "Latte"}, 2: {"nombre": "Capuchino"}}

    resultado = mapa_ingrediente_a_productos(recetas_por_producto, productos_por_id)

    assert sorted(resultado[9]) == ["Capuchino", "Latte"]


def test_riesgo_inventario_solo_incluye_bajo_stock_minimo():
    ingredientes = [
        {"id": 1, "nombre": "Leche", "unidad": "ml", "stock_actual": "500", "stock_minimo": "1000", "costo_unitario": "0.02"},
        {"id": 2, "nombre": "Café", "unidad": "g", "stock_actual": "5000", "stock_minimo": "1000", "costo_unitario": "0.10"},
    ]
    mapa = {1: ["Latte", "Capuchino"], 2: ["Espresso"]}

    resultado = riesgo_inventario(ingredientes, mapa)

    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Leche"
    assert resultado[0]["falta"] == Decimal("500")
    assert resultado[0]["costo_reposicion"] == Decimal("10.00")
    assert resultado[0]["productos_afectados"] == ["Latte", "Capuchino"]
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd web-admin && python -m pytest tests/test_reportes.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.reportes'`

- [ ] **Step 3: Implementar `app/reportes.py`**

```python
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal


def periodo_anterior(desde: date, hasta: date) -> tuple[date, date]:
    duracion = hasta - desde
    return desde - duracion - timedelta(days=0), desde


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


def costo_receta(receta: list[dict]) -> Decimal:
    total = Decimal("0")
    for item in receta:
        cantidad = _dec(item["cantidad_requerida"])
        costo_unitario = _dec(item["ingrediente"]["costo_unitario"])
        total += cantidad * costo_unitario
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ranking_margen(top_productos: list[dict], costos_por_producto: dict[int, Decimal]) -> list[dict]:
    filas = []
    for producto in top_productos:
        producto_id = producto["producto_id"]
        cantidad = int(producto["cantidad_vendida"]) or 1
        ingresos = _dec(producto["ingresos"])
        costo_unitario_total = costos_por_producto.get(producto_id, Decimal("0"))
        costo_total = costo_unitario_total * cantidad
        margen = ingresos - costo_total
        margen_pct = calcular_margen_pct(ingresos, margen)
        filas.append(
            {
                "producto_id": producto_id,
                "nombre": producto["nombre"],
                "ingresos": ingresos,
                "costo_total": costo_total,
                "margen": margen,
                "margen_pct": margen_pct,
            }
        )
    return sorted(filas, key=lambda fila: fila["margen_pct"])


def mapa_ingrediente_a_productos(
    recetas_por_producto: dict[int, list[dict]], productos_por_id: dict[int, dict]
) -> dict[int, list[str]]:
    mapa: dict[int, list[str]] = {}
    for producto_id, receta in recetas_por_producto.items():
        nombre_producto = productos_por_id[producto_id]["nombre"]
        for item in receta:
            mapa.setdefault(item["id_ingrediente"], []).append(nombre_producto)
    return mapa


def riesgo_inventario(ingredientes: list[dict], mapa: dict[int, list[str]]) -> list[dict]:
    filas = []
    for ingrediente in ingredientes:
        stock_actual = _dec(ingrediente["stock_actual"])
        stock_minimo = _dec(ingrediente["stock_minimo"])
        if stock_actual >= stock_minimo:
            continue
        falta = stock_minimo - stock_actual
        costo_unitario = _dec(ingrediente["costo_unitario"])
        filas.append(
            {
                "id": ingrediente["id"],
                "nombre": ingrediente["nombre"],
                "unidad": ingrediente["unidad"],
                "stock_actual": stock_actual,
                "stock_minimo": stock_minimo,
                "falta": falta,
                "costo_reposicion": (falta * costo_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "productos_afectados": mapa.get(ingrediente["id"], []),
            }
        )
    return sorted(filas, key=lambda fila: fila["falta"], reverse=True)
```

- [ ] **Step 4: Correr los tests de nuevo**

Run: `cd web-admin && python -m pytest tests/test_reportes.py -v`
Expected: 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add web-admin/app/reportes.py web-admin/tests/test_reportes.py
git commit -m "feat(web-admin): calculos de reportes accionables (margen, riesgo de inventario)"
```

---

### Task 11: Dashboard (blueprint + template con Chart.js)

**Files:**
- Create: `web-admin/app/blueprints/dashboard.py`
- Create: `web-admin/app/templates/dashboard.html`
- Modify: `web-admin/app/__init__.py` (quitar `_placeholder_root`, registrar blueprint `dashboard` con ruta `/`)
- Test: `web-admin/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `api_client.obtener_reporte_admin`, `api_client.listar_productos`, `api_client.listar_ingredientes`, `api_client.listar_receta_producto`, todas las funciones de `app.reportes` (Task 10).
- Produces: blueprint `dashboard`, ruta `GET /` (`dashboard.index`), acepta query params `desde`/`hasta` (formato `YYYY-MM-DD`, default: últimos 30 días).

- [ ] **Step 1: Escribir el test primero**

Crear `web-admin/tests/test_dashboard.py`:

```python
import responses

BASE_URL = "http://testserver"


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


def _mock_reporte(desde_iso, hasta_iso, total_ventas="1000.00", total_gastos="400.00"):
    return {
        "desde": desde_iso,
        "hasta": hasta_iso,
        "total_ventas": total_ventas,
        "total_gastos": total_gastos,
        "ganancia_neta": str(float(total_ventas) - float(total_gastos)),
        "top_productos": [
            {"producto_id": 1, "nombre": "Latte", "cantidad_vendida": 20, "ingresos": "600.00"}
        ],
    }


@responses.activate
def test_dashboard_muestra_margen_y_variacion(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes",
        json=_mock_reporte("2026-06-01T00:00:00", "2026-06-30T00:00:00"),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/producto_ingrediente",
        json=[
            {
                "id_producto": 1,
                "id_ingrediente": 2,
                "cantidad_requerida": "200.00",
                "ingrediente": {"id": 2, "nombre": "Leche entera", "unidad": "ml", "costo_unitario": "0.02"},
            }
        ],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/ingredientes",
        json=[
            {
                "id": 2,
                "nombre": "Leche entera",
                "unidad": "ml",
                "stock_actual": "500",
                "stock_minimo": "1000",
                "costo_unitario": "0.02",
                "activo": True,
            }
        ],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[{"id": 1, "nombre": "Latte", "categoria": {"id": 1, "nombre": "Bebidas calientes"}}],
        status=200,
    )

    respuesta = client.get("/?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "Ganancia neta" in cuerpo
    assert "Leche entera" in cuerpo


def test_dashboard_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd web-admin && python -m pytest tests/test_dashboard.py -v`
Expected: FAIL (la ruta `/` actual es el placeholder que redirige siempre a `/login`, sin importar la sesión)

- [ ] **Step 3: Implementar el blueprint**

Crear `web-admin/app/blueprints/dashboard.py`:

```python
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request

from app.api_client import (
    listar_ingredientes,
    listar_productos,
    listar_receta_producto,
    obtener_reporte_admin,
)
from app.auth import api_base_url, current_token, login_required
from app.reportes import (
    calcular_margen_pct,
    costo_receta,
    mapa_ingrediente_a_productos,
    periodo_anterior,
    ranking_margen,
    riesgo_inventario,
    variacion_pct,
)

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

    reporte_actual = obtener_reporte_admin(base_url, token, desde.isoformat(), hasta.isoformat())
    desde_prev, hasta_prev = periodo_anterior(desde, hasta)
    reporte_anterior = obtener_reporte_admin(base_url, token, desde_prev.isoformat(), hasta_prev.isoformat())

    margen_actual = calcular_margen_pct(reporte_actual["total_ventas"], reporte_actual["ganancia_neta"])
    margen_anterior = calcular_margen_pct(reporte_anterior["total_ventas"], reporte_anterior["ganancia_neta"])
    variacion_ventas = variacion_pct(reporte_actual["total_ventas"], reporte_anterior["total_ventas"])
    variacion_ganancia = variacion_pct(reporte_actual["ganancia_neta"], reporte_anterior["ganancia_neta"])

    top_productos = reporte_actual["top_productos"]
    costos_por_producto = {}
    for producto in top_productos:
        receta = listar_receta_producto(base_url, token, producto["producto_id"])
        costos_por_producto[producto["producto_id"]] = costo_receta(receta) if receta else 0
    ranking = ranking_margen(top_productos, costos_por_producto)

    productos = listar_productos(base_url, token)
    productos_por_id = {p["id"]: p for p in productos}
    recetas_por_producto = {p["id"]: listar_receta_producto(base_url, token, p["id"]) for p in productos}
    mapa = mapa_ingrediente_a_productos(recetas_por_producto, productos_por_id)

    ingredientes = listar_ingredientes(base_url, token)
    riesgo = riesgo_inventario(ingredientes, mapa)

    return render_template(
        "dashboard.html",
        desde=desde,
        hasta=hasta,
        reporte=reporte_actual,
        margen_actual=margen_actual,
        margen_anterior=margen_anterior,
        variacion_ventas=variacion_ventas,
        variacion_ganancia=variacion_ganancia,
        ranking=ranking,
        riesgo=riesgo,
    )
```

Nota de rendimiento: `recetas_por_producto` hace una llamada por producto del catálogo — aceptable para un menú de cafetería (decenas de productos), y es la única forma de derivar el mapa ingrediente→productos sin tocar la base de datos directamente (restricción del CLAUDE.md). Si el catálogo creciera mucho, se optimizaría cacheando esta llamada por request (fuera de alcance actual).

- [ ] **Step 4: Crear la plantilla**

Crear `web-admin/app/templates/dashboard.html`:

```html
{% extends "base.html" %}
{% block title %}Dashboard — Coffee Code Admin{% endblock %}
{% block content %}
<div class="mb-6 flex items-center justify-between">
  <h1 class="text-2xl font-serif">Dashboard</h1>
  <form method="get" class="flex items-center gap-2 text-sm">
    <input type="date" name="desde" value="{{ desde.isoformat() }}" class="rounded-lg border border-caramel/40 px-3 py-1.5">
    <span class="text-coffee">a</span>
    <input type="date" name="hasta" value="{{ hasta.isoformat() }}" class="rounded-lg border border-caramel/40 px-3 py-1.5">
    <button type="submit" class="bg-espresso text-cream px-3 py-1.5 rounded-lg hover:bg-coffee">Filtrar</button>
    <a href="{{ url_for('reportes.exportar_pdf', desde=desde.isoformat(), hasta=hasta.isoformat()) }}" class="px-3 py-1.5 rounded-lg border border-caramel/40 hover:bg-cream">PDF</a>
    <a href="{{ url_for('reportes.exportar_xlsx', desde=desde.isoformat(), hasta=hasta.isoformat()) }}" class="px-3 py-1.5 rounded-lg border border-caramel/40 hover:bg-cream">XLSX</a>
  </form>
</div>

<div class="grid grid-cols-4 gap-4 mb-8">
  <div class="card p-5">
    <div class="text-xs uppercase text-coffee">Ventas</div>
    <div class="text-2xl font-serif mt-1">${{ "%.2f"|format(reporte.total_ventas|float) }}</div>
    {% if variacion_ventas is not none %}
    <div class="text-xs mt-1 {{ 'text-green-700' if variacion_ventas >= 0 else 'text-red-700' }}">
      {{ "+" if variacion_ventas >= 0 else "" }}{{ variacion_ventas }}% vs. periodo anterior
    </div>
    {% endif %}
  </div>
  <div class="card p-5">
    <div class="text-xs uppercase text-coffee">Gastos</div>
    <div class="text-2xl font-serif mt-1">${{ "%.2f"|format(reporte.total_gastos|float) }}</div>
  </div>
  <div class="card p-5">
    <div class="text-xs uppercase text-coffee">Ganancia neta</div>
    <div class="text-2xl font-serif mt-1">${{ "%.2f"|format(reporte.ganancia_neta|float) }}</div>
    {% if variacion_ganancia is not none %}
    <div class="text-xs mt-1 {{ 'text-green-700' if variacion_ganancia >= 0 else 'text-red-700' }}">
      {{ "+" if variacion_ganancia >= 0 else "" }}{{ variacion_ganancia }}% vs. periodo anterior
    </div>
    {% endif %}
  </div>
  <div class="card p-5">
    <div class="text-xs uppercase text-coffee">Margen</div>
    <div class="text-2xl font-serif mt-1">{{ margen_actual }}%</div>
    <div class="text-xs mt-1 text-coffee">Periodo anterior: {{ margen_anterior }}%</div>
  </div>
</div>

<div class="grid grid-cols-2 gap-6 mb-8">
  <div class="card p-5">
    <h2 class="font-serif text-lg mb-3">Ventas vs. gastos</h2>
    <canvas id="chartVentasGastos" height="180"></canvas>
  </div>
  <div class="card p-5">
    <h2 class="font-serif text-lg mb-3">Ranking de margen por producto</h2>
    <canvas id="chartMargen" height="180"></canvas>
  </div>
</div>

<div class="card p-5 mb-8">
  <h2 class="font-serif text-lg mb-3">Rendimiento de producto</h2>
  <table class="w-full text-sm">
    <thead class="text-left text-xs uppercase tracking-wide text-coffee">
      <tr>
        <th class="py-2">Producto</th>
        <th class="py-2">Ingresos</th>
        <th class="py-2">Costo estimado</th>
        <th class="py-2">Margen</th>
        <th class="py-2">Margen %</th>
      </tr>
    </thead>
    <tbody>
      {% for fila in ranking %}
      <tr class="border-t border-caramel/20">
        <td class="py-2">{{ fila.nombre }}</td>
        <td class="py-2">${{ "%.2f"|format(fila.ingresos) }}</td>
        <td class="py-2">${{ "%.2f"|format(fila.costo_total) }}</td>
        <td class="py-2">${{ "%.2f"|format(fila.margen) }}</td>
        <td class="py-2">{{ fila.margen_pct }}%</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<div class="card p-5">
  <h2 class="font-serif text-lg mb-3">Riesgo de inventario</h2>
  {% if riesgo %}
  <table class="w-full text-sm">
    <thead class="text-left text-xs uppercase tracking-wide text-coffee">
      <tr>
        <th class="py-2">Ingrediente</th>
        <th class="py-2">Falta</th>
        <th class="py-2">Costo de reposición</th>
        <th class="py-2">Productos afectados</th>
      </tr>
    </thead>
    <tbody>
      {% for fila in riesgo %}
      <tr class="border-t border-caramel/20 bg-red-50">
        <td class="py-2">{{ fila.nombre }}</td>
        <td class="py-2">{{ fila.falta }} {{ fila.unidad }}</td>
        <td class="py-2">${{ "%.2f"|format(fila.costo_reposicion) }}</td>
        <td class="py-2">{{ fila.productos_afectados | join(", ") }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="text-green-700 text-sm">Sin ingredientes bajo el stock mínimo.</p>
  {% endif %}
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
        data: [{{ reporte.total_ventas }}, {{ reporte.total_gastos }}, {{ reporte.ganancia_neta }}],
        backgroundColor: [coffeeChartPalette.coffee, coffeeChartPalette.negative, coffeeChartPalette.positive],
      }]
    },
    options: { plugins: { legend: { display: false } } }
  });

  new Chart(document.getElementById('chartMargen'), {
    type: 'bar',
    data: {
      labels: [{% for fila in ranking %}{{ fila.nombre|tojson }},{% endfor %}],
      datasets: [{
        label: 'Margen %',
        data: [{% for fila in ranking %}{{ fila.margen_pct }},{% endfor %}],
        backgroundColor: coffeeChartPalette.caramel,
      }]
    },
    options: { indexAxis: 'y', plugins: { legend: { display: false } } }
  });
</script>
{% endblock %}
```

- [ ] **Step 5: Registrar el blueprint y quitar el placeholder**

En `web-admin/app/__init__.py`, quitar la función `_placeholder_root` y su `@app.get("/")`, y agregar el registro del blueprint junto a los demás:

```python
    from app.blueprints.dashboard import bp as dashboard_bp

    app.register_blueprint(dashboard_bp)
```

- [ ] **Step 6: Correr todos los tests de web-admin**

Run: `cd web-admin && python -m pytest tests/ -v`
Expected: todos PASS, incluyendo `test_ruta_protegida_sin_sesion_redirige_a_login` de Task 5 (ahora `/` está realmente detrás de `@login_required`)

- [ ] **Step 7: Commit**

```bash
git add web-admin/app/blueprints/dashboard.py web-admin/app/templates/dashboard.html web-admin/app/__init__.py web-admin/tests/test_dashboard.py
git commit -m "feat(web-admin): dashboard con reportes accionables y graficas"
```

---

### Task 12: Exportación PDF y XLSX

**Files:**
- Create: `web-admin/app/blueprints/reportes.py`
- Create: `web-admin/app/templates/reportes/reporte_pdf.html`
- Modify: `web-admin/app/__init__.py`
- Test: `web-admin/tests/test_reportes_export.py`

**Interfaces:**
- Consumes: mismos datos que Task 11 (`obtener_reporte_admin`, `app.reportes.*`).
- Produces: blueprint `reportes`, rutas `GET /reportes/exportar.pdf` (`reportes.exportar_pdf`), `GET /reportes/exportar.xlsx` (`reportes.exportar_xlsx`), ambas reciben `desde`/`hasta` como query params.

- [ ] **Step 1: Escribir el test primero**

Crear `web-admin/tests/test_reportes_export.py`:

```python
import responses

BASE_URL = "http://testserver"


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


def _mock_endpoints():
    reporte = {
        "desde": "2026-06-01T00:00:00",
        "hasta": "2026-06-30T00:00:00",
        "total_ventas": "1000.00",
        "total_gastos": "400.00",
        "ganancia_neta": "600.00",
        "top_productos": [
            {"producto_id": 1, "nombre": "Latte", "cantidad_vendida": 20, "ingresos": "600.00"}
        ],
    }
    responses.add(responses.GET, f"{BASE_URL}/api/reportes", json=reporte, status=200)
    responses.add(responses.GET, f"{BASE_URL}/producto_ingrediente", json=[], status=200)
    responses.add(responses.GET, f"{BASE_URL}/productos", json=[{"id": 1, "nombre": "Latte", "categoria": {"id": 1, "nombre": "Bebidas"}}], status=200)
    responses.add(
        responses.GET,
        f"{BASE_URL}/ingredientes",
        json=[{"id": 1, "nombre": "Leche", "unidad": "ml", "stock_actual": "500", "stock_minimo": "1000", "costo_unitario": "0.02", "activo": True}],
        status=200,
    )


@responses.activate
def test_exportar_pdf_devuelve_content_type_pdf(client):
    _login_como_admin(client)
    _mock_endpoints()

    respuesta = client.get("/reportes/exportar.pdf?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    assert respuesta.content_type == "application/pdf"
    assert respuesta.data[:4] == b"%PDF"


@responses.activate
def test_exportar_xlsx_devuelve_content_type_correcto(client):
    _login_como_admin(client)
    _mock_endpoints()

    respuesta = client.get("/reportes/exportar.xlsx?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    assert respuesta.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `cd web-admin && python -m pytest tests/test_reportes_export.py -v`
Expected: FAIL (404, blueprint no existe)

- [ ] **Step 3: Implementar el blueprint**

Crear `web-admin/app/blueprints/reportes.py`:

```python
import io
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, render_template, request
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from weasyprint import HTML

from app.api_client import (
    listar_ingredientes,
    listar_productos,
    listar_receta_producto,
    obtener_reporte_admin,
)
from app.auth import api_base_url, current_token, login_required
from app.reportes import (
    calcular_margen_pct,
    costo_receta,
    mapa_ingrediente_a_productos,
    ranking_margen,
    riesgo_inventario,
)

bp = Blueprint("reportes", __name__, url_prefix="/reportes")


def _parsear_fecha(valor: str | None, default: date) -> date:
    if not valor:
        return default
    return datetime.strptime(valor, "%Y-%m-%d").date()


def _construir_datos_reporte(desde: date, hasta: date) -> dict:
    token = current_token()
    base_url = api_base_url()

    reporte = obtener_reporte_admin(base_url, token, desde.isoformat(), hasta.isoformat())
    margen = calcular_margen_pct(reporte["total_ventas"], reporte["ganancia_neta"])

    top_productos = reporte["top_productos"]
    costos_por_producto = {}
    for producto in top_productos:
        receta = listar_receta_producto(base_url, token, producto["producto_id"])
        costos_por_producto[producto["producto_id"]] = costo_receta(receta) if receta else 0
    ranking = ranking_margen(top_productos, costos_por_producto)

    productos = listar_productos(base_url, token)
    productos_por_id = {p["id"]: p for p in productos}
    recetas_por_producto = {p["id"]: listar_receta_producto(base_url, token, p["id"]) for p in productos}
    mapa = mapa_ingrediente_a_productos(recetas_por_producto, productos_por_id)

    ingredientes = listar_ingredientes(base_url, token)
    riesgo = riesgo_inventario(ingredientes, mapa)

    return {"desde": desde, "hasta": hasta, "reporte": reporte, "margen": margen, "ranking": ranking, "riesgo": riesgo}


@bp.route("/exportar.pdf")
@login_required
def exportar_pdf():
    hoy = date.today()
    hasta = _parsear_fecha(request.args.get("hasta"), hoy)
    desde = _parsear_fecha(request.args.get("desde"), hoy - timedelta(days=30))

    datos = _construir_datos_reporte(desde, hasta)
    html_renderizado = render_template("reportes/reporte_pdf.html", **datos)
    pdf_bytes = HTML(string=html_renderizado).write_pdf()

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_{desde}_a_{hasta}.pdf"},
    )


@bp.route("/exportar.xlsx")
@login_required
def exportar_xlsx():
    hoy = date.today()
    hasta = _parsear_fecha(request.args.get("hasta"), hoy)
    desde = _parsear_fecha(request.args.get("desde"), hoy - timedelta(days=30))

    datos = _construir_datos_reporte(desde, hasta)

    libro = Workbook()
    encabezado_relleno = PatternFill(start_color="6F4E37", end_color="6F4E37", fill_type="solid")
    encabezado_fuente = Font(color="F5E6D3", bold=True)

    hoja_resumen = libro.active
    hoja_resumen.title = "Resumen financiero"
    hoja_resumen.append(["Métrica", "Valor"])
    for celda in hoja_resumen[1]:
        celda.fill = encabezado_relleno
        celda.font = encabezado_fuente
    hoja_resumen.append(["Ventas", float(datos["reporte"]["total_ventas"])])
    hoja_resumen.append(["Gastos", float(datos["reporte"]["total_gastos"])])
    hoja_resumen.append(["Ganancia neta", float(datos["reporte"]["ganancia_neta"])])
    hoja_resumen.append(["Margen %", float(datos["margen"])])

    hoja_ranking = libro.create_sheet("Rendimiento de producto")
    hoja_ranking.append(["Producto", "Ingresos", "Costo estimado", "Margen", "Margen %"])
    for celda in hoja_ranking[1]:
        celda.fill = encabezado_relleno
        celda.font = encabezado_fuente
    for fila in datos["ranking"]:
        hoja_ranking.append(
            [fila["nombre"], float(fila["ingresos"]), float(fila["costo_total"]), float(fila["margen"]), float(fila["margen_pct"])]
        )

    hoja_riesgo = libro.create_sheet("Riesgo de inventario")
    hoja_riesgo.append(["Ingrediente", "Falta", "Unidad", "Costo de reposición", "Productos afectados"])
    for celda in hoja_riesgo[1]:
        celda.fill = encabezado_relleno
        celda.font = encabezado_fuente
    for fila in datos["riesgo"]:
        hoja_riesgo.append(
            [fila["nombre"], float(fila["falta"]), fila["unidad"], float(fila["costo_reposicion"]), ", ".join(fila["productos_afectados"])]
        )

    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)

    return Response(
        buffer.read(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reporte_{desde}_a_{hasta}.xlsx"},
    )
```

- [ ] **Step 4: Crear la plantilla PDF**

Crear `web-admin/app/templates/reportes/reporte_pdf.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: 'Helvetica', sans-serif; color: #3B2412; }
    h1 { color: #3B2412; margin-bottom: 0; }
    .subtitulo { color: #6F4E37; margin-top: 4px; margin-bottom: 24px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
    th { background: #6F4E37; color: #F5E6D3; text-align: left; padding: 8px; font-size: 12px; }
    td { padding: 8px; border-bottom: 1px solid #E5D5BE; font-size: 12px; }
    .kpis { display: flex; gap: 16px; margin-bottom: 24px; }
    .kpi { border: 1px solid #E5D5BE; border-radius: 8px; padding: 12px 16px; flex: 1; }
    .kpi .valor { font-size: 20px; font-weight: bold; }
  </style>
</head>
<body>
  <h1>Coffee Code — Reporte de Administración</h1>
  <p class="subtitulo">Periodo: {{ desde.strftime('%d/%m/%Y') }} — {{ hasta.strftime('%d/%m/%Y') }}</p>

  <div class="kpis">
    <div class="kpi"><div>Ventas</div><div class="valor">${{ "%.2f"|format(reporte.total_ventas|float) }}</div></div>
    <div class="kpi"><div>Gastos</div><div class="valor">${{ "%.2f"|format(reporte.total_gastos|float) }}</div></div>
    <div class="kpi"><div>Ganancia neta</div><div class="valor">${{ "%.2f"|format(reporte.ganancia_neta|float) }}</div></div>
    <div class="kpi"><div>Margen</div><div class="valor">{{ margen }}%</div></div>
  </div>

  <h3>Rendimiento de producto</h3>
  <table>
    <tr><th>Producto</th><th>Ingresos</th><th>Costo estimado</th><th>Margen</th><th>Margen %</th></tr>
    {% for fila in ranking %}
    <tr>
      <td>{{ fila.nombre }}</td>
      <td>${{ "%.2f"|format(fila.ingresos) }}</td>
      <td>${{ "%.2f"|format(fila.costo_total) }}</td>
      <td>${{ "%.2f"|format(fila.margen) }}</td>
      <td>{{ fila.margen_pct }}%</td>
    </tr>
    {% endfor %}
  </table>

  <h3>Riesgo de inventario</h3>
  {% if riesgo %}
  <table>
    <tr><th>Ingrediente</th><th>Falta</th><th>Costo de reposición</th><th>Productos afectados</th></tr>
    {% for fila in riesgo %}
    <tr>
      <td>{{ fila.nombre }}</td>
      <td>{{ fila.falta }} {{ fila.unidad }}</td>
      <td>${{ "%.2f"|format(fila.costo_reposicion) }}</td>
      <td>{{ fila.productos_afectados | join(", ") }}</td>
    </tr>
    {% endfor %}
  </table>
  {% else %}
  <p>Sin ingredientes bajo el stock mínimo.</p>
  {% endif %}
</body>
</html>
```

- [ ] **Step 5: Registrar el blueprint**

En `web-admin/app/__init__.py`:

```python
    from app.blueprints.reportes import bp as reportes_bp

    app.register_blueprint(reportes_bp)
```

- [ ] **Step 6: Correr los tests**

Run: `cd web-admin && python -m pytest tests/test_reportes_export.py -v`
Expected: 2 tests PASS

- [ ] **Step 7: Correr toda la suite de web-admin**

Run: `cd web-admin && python -m pytest tests/ -v`
Expected: todos PASS

- [ ] **Step 8: Commit**

```bash
git add web-admin/app/blueprints/reportes.py web-admin/app/templates/reportes/ web-admin/app/__init__.py web-admin/tests/test_reportes_export.py
git commit -m "feat(web-admin): exportacion de reportes a PDF y XLSX"
```

---

### Task 13: Verificación end-to-end contra Docker real + README

**Files:**
- Modify: `README.md` (quitar "*(próximamente)*" del panel admin, documentar cómo levantarlo)
- Test: verificación manual (no automatizada)

**Interfaces:** ninguna nueva — este task valida que todo lo anterior funciona junto contra la API real.

- [ ] **Step 1: Levantar todo el stack**

Run: `docker compose up -d --build`
Expected: los 3 contenedores (`coffee_code_db`, `coffee_code_api`, `coffee_code_web`) quedan `Up`.

- [ ] **Step 2: Aplicar migraciones y seed si hace falta**

Run: `cd api && python -m alembic upgrade head && python -m app.seed`
Expected: sin errores (idempotente si ya se corrió antes).

- [ ] **Step 3: Verificación manual del flujo completo**

Abrir `http://localhost:8020/login` en el navegador y verificar, con `admin@coffeecode.com` / `Admin123!`:
1. Login exitoso redirige al dashboard con KPIs, gráficas y las tablas de ranking de margen y riesgo de inventario pobladas con datos reales del seed.
2. Exportar PDF y XLSX descargan archivos válidos (abren sin error).
3. Usuarios: crear un usuario nuevo, editarlo, cambiar su rol, desactivarlo — verificar que los cambios persisten recargando la página.
4. Productos: crear un producto nuevo en una categoría existente, editarlo, desactivarlo.
5. Ingredientes: crear un ingrediente, ajustar su stock (positivo y negativo), verificar que un ingrediente con stock bajo aparece marcado y en el bloque de riesgo de inventario del dashboard.
6. Recetas: seleccionar un producto, agregar un ingrediente a su receta, quitarlo.
7. Intentar login con un usuario que no sea Administrador (ej. `mesero@coffeecode.com` / `Mesero123!`) y confirmar que es rechazado con el mensaje correcto.
8. Cerrar sesión y confirmar que las rutas protegidas vuelven a redirigir a `/login`.

- [ ] **Step 4: Correr toda la suite de tests (API + web-admin)**

Run: `cd api && python -m pytest app/tests/ -v`
Expected: todos PASS (15 originales + los agregados en Tasks 1-2)

Run: `cd web-admin && python -m pytest tests/ -v`
Expected: todos PASS

- [ ] **Step 5: Actualizar el README**

En `README.md`, cambiar la fila de la tabla de arquitectura:

```
| **Panel Admin** | `Flask` | Usuarios/roles, estadísticas, export PDF/XLSX. Consume la API, no toca la BD. |
```

(quitar `*(próximamente)*`), y en la sección "Levantar el proyecto" agregar después del bloque de `docker compose up`:

```
La Web Admin queda en **`http://localhost:8020`**.
```

Y en "Estructura del repo", cambiar:

```
├── web-admin/            # Flask — panel de administración
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: documentar el panel Web Admin ya disponible"
```

## Self-Review

**Spec coverage:**
- Login solo Administrador → Task 5. ✓
- Usuarios/roles CRUD → Task 6. ✓
- Productos/Ingredientes/Recetas CRUD → Tasks 7, 8, 9 (más Tasks 1-2 en la API para soportarlos). ✓
- Reportes accionables (margen, comparación de periodo, ranking de margen, riesgo de inventario) → Tasks 10, 11. ✓
- Export PDF/XLSX → Task 12. ✓
- Servicio Docker nuevo → Task 3. ✓
- Sistema visual de marca → Task 5 (`base.html`, `theme.css`, paleta Tailwind) aplicado en todas las plantillas subsecuentes. ✓
- Manejo de errores (401/403/422) → Task 5 (`errorhandler`) + `flash()` en cada blueprint. ✓
- Postman para endpoints nuevos de la API → Tasks 1, 2. ✓
- Verificación end-to-end real → Task 13. ✓

**Placeholder scan:** sin TBD/TODO; todos los pasos de código incluyen el código completo, no referencias a "similar a Task N".

**Type consistency:** `api_client.py` (Task 4) define la firma exacta de cada función una sola vez; todos los blueprints posteriores (Tasks 6-12) la consumen tal cual, sin redefinir nombres. `app/reportes.py` (Task 10) define las firmas que Tasks 11 y 12 reutilizan sin cambios.
