<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:6F4E37,100:3B2412&height=220&section=header&text=Coffee%20Code&fontSize=70&fontColor=F5E6D3&fontAlignY=38&desc=Sistema%20Integral%20de%20Administraci%C3%B3n%20de%20Cafeter%C3%ADa&descAlignY=58&descSize=18&animation=fadeIn" />

<br/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=16&duration=2500&pause=900&color=6F4E37&center=true&vCenter=true&width=560&lines=Pedidos+en+tiempo+real+%E2%98%95;Cocina+%E2%86%92+Mesero+%E2%86%92+Caja+sin+friction;FastAPI+%2B+PostgreSQL+%2B+WebSockets;Hecho+con+mucho+caf%C3%A9" alt="Typing SVG" />

<br/><br/>

[![Python](https://img.shields.io/badge/Python-3.12-6F4E37?style=for-the-badge&logo=python&logoColor=F5E6D3)](api/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-A87C5F?style=for-the-badge&logo=fastapi&logoColor=F5E6D3)](api/app/main.py)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-3B2412?style=for-the-badge&logo=postgresql&logoColor=F5E6D3)](docker-compose.yml)
[![Docker](https://img.shields.io/badge/Docker-Compose-6F4E37?style=for-the-badge&logo=docker&logoColor=F5E6D3)](docker-compose.yml)
[![Pytest](https://img.shields.io/badge/Tests-15%20passed-A87C5F?style=for-the-badge&logo=pytest&logoColor=F5E6D3)](api/app/tests)
[![Postman](https://img.shields.io/badge/Postman-validado-3B2412?style=for-the-badge&logo=postman&logoColor=F5E6D3)](postman/coffee-code.postman_collection.json)

</div>

<br/>

> ☕ **Coffee Code** es el sistema digital que reemplaza la operación manual de una cafetería: pedidos, cocina, caja e inventario en un solo flujo, en tiempo real, sin papelitos perdidos ni gritos a través del mostrador.
>
> Proyecto académico — Ingeniería en Sistemas Computacionales (UPQ). Asesor: ISC Iván Isay Guerra López.

<br/>

<div align="center">

### 🫘 Tabla de contenidos

[Arquitectura](#%EF%B8%8F-arquitectura) · [Modelo de datos](#-modelo-de-datos) · [Endpoints](#-endpoints) · [Tiempo real](#-tiempo-real-websockets) · [Levantar el proyecto](#-levantar-el-proyecto) · [Testing](#-testing) · [Estructura](#-estructura-del-repo) · [Equipo](#-equipo)

</div>

---

## ☕ El problema

Una cafetería que opera sin sistema digital integrado pierde tiempo y dinero en tres puntos exactos: el mesero no sabe si cocina ya vio el pedido, cocina no sabe si ya se cobró, y caja no sabe qué se vendió hasta el corte del día. **Coffee Code** ataca eso con un núcleo único de lógica de negocio (FastAPI) que tres roles —Mesero, Cocina, Caja— consultan en tiempo real desde sus propios dispositivos, más un panel de Administración para gobernar usuarios, productos y reportes.

<br/>

## 🏗️ Arquitectura

<div align="center">

| Componente | Tecnología | Responsabilidad |
|:--|:--|:--|
| ☕ **API Central** | `FastAPI` + `Python 3.12` | Única capa que toca PostgreSQL. Toda la lógica de negocio, JWT, WebSockets. |
| 📱 **Cliente Móvil** | `React Native` + `Expo` | App por rol: Mesero, Cocina, Caja. *(próximamente)* |
| 🖥️ **Panel Admin** | `Flask` | Usuarios/roles, estadísticas, export PDF/XLSX. Consume la API, no toca la BD. *(próximamente)* |
| 🗄️ **Base de datos** | `PostgreSQL 15` | Única fuente de verdad — modelo 2FN, 16 entidades. |

</div>

```
            ┌──────────────┐         ┌──────────────────────┐
 Mesero ──▶ │              │         │                      │
            │   FastAPI    │ ◀─────▶ │   PostgreSQL 15      │
 Cocina ──▶ │   API Core   │         │   (única verdad)     │
            │ JWT + WS     │         │                      │
  Caja  ──▶ │              │         └──────────────────────┘
            └──────┬───────┘
                   │ consumida por
                   ▼
            ┌──────────────┐
            │  Flask Admin │
            └──────────────┘
```

<br/>

## 🫘 Modelo de datos

16 tablas en 2FN, fieles al diccionario de datos del análisis original — sin atajos ni `create_all` silencioso, todo versionado con **Alembic**.

<details>
<summary><b>Ver entidades principales</b></summary>
<br/>

```
ROLES ─┬─ USUARIOS ─┬─ PEDIDOS ──┬── DETALLE_PEDIDOS ── PRODUCTOS ── RECETAS ── INGREDIENTES
       │            │            │
       │            └─ GASTOS    └── TICKETS (1:1) ── PAGOS (1:1) ── METODOS_PAGO
       │
MESAS ─┴─ ESTATUS_MESAS          ESTATUS_PEDIDOS · ESTATUS_COCINA · CATEGORIAS
```

</details>

<br/>

## 📋 Endpoints

<details>
<summary><b>🧑‍🍳 Mesero</b></summary>
<br/>

| Método | Ruta | Descripción |
|:--|:--|:--|
| `GET` | `/mesas` | Lista de mesas con estatus |
| `POST` | `/pedidos` | Crear pedido (transacción, valida no-vacío) |
| `GET` | `/pedidos`, `/pedidos/{id}` | Consultar pedidos |
| `PUT` | `/pedidos/{id}/estado` | Cambiar estado (libera mesa al entregar) |

</details>

<details>
<summary><b>💰 Caja</b></summary>
<br/>

| Método | Ruta | Descripción |
|:--|:--|:--|
| `POST` | `/ventas` | Ticket + pago, IVA 16%, bloquea pagos duplicados |
| `POST` | `/gastos` | Registrar gasto |
| `POST` | `/compras` | Compra de insumo (gasto + incrementa stock) |
| `GET` | `/caja/resumen` | Ventas, gastos y ganancia neta del periodo |

</details>

<details>
<summary><b>🔥 Cocina</b></summary>
<br/>

| Método | Ruta | Descripción |
|:--|:--|:--|
| `GET/POST/PUT/DELETE` | `/productos` | CRUD de productos (delete = soft-delete) |
| `GET/POST` | `/ingredientes` · `PUT /ingredientes/{id}/stock` | Inventario |
| `POST` | `/producto_ingrediente` | Receta (producto ↔ ingrediente) |
| `GET` | `/pedidos?estado=Pendiente` | Cola FIFO de cocina |
| `PUT` | `/pedidos/{id}/estado` | Pendiente → En preparación → **Listo** (descuento atómico de inventario + alerta de stock bajo) |

</details>

<details>
<summary><b>🛠️ Administración</b></summary>
<br/>

| Método | Ruta | Descripción |
|:--|:--|:--|
| `GET/POST/PUT` | `/api/usuarios` | Gestión de usuarios y roles |
| `GET` | `/api/reportes` | Ventas, gastos, ganancia y top productos agregados |

</details>

<br/>

## ⚡ Tiempo real (WebSockets)

```
ws://<host>/ws/{canal}?token=<jwt>      canal ∈ { mesero, cocina, caja }
```

| Evento | Disparado por | Lo recibe |
|:--|:--|:--|
| `nuevo_pedido` | Mesero crea un pedido | Canal `cocina` |
| `pedido_activado` | Cocina pasa el pedido a *En preparación* | Canales `mesero` y `caja` |
| `pedido_listo` | Cocina marca el pedido como *Listo* | Canal `mesero` |

<br/>

## 🚀 Levantar el proyecto

```bash
git clone https://github.com/EmilianoLedesma/Coffe_Code_App.git
cd Coffe_Code_App

cp api/.env.example api/.env        # ajusta JWT_SECRET si lo vas a exponer

docker compose up -d --build        # levanta Postgres + API

cd api
python -m alembic upgrade head      # migraciones
python -m app.seed                  # catálogo + menú de demo
```

La API queda en **`http://localhost:8010`** · Swagger interactivo en **`/docs`**.

<div align="center">

| Usuario demo | Rol |
|:--|:--|
| `admin@coffeecode.com` / `Admin123!` | Administrador |
| `mesero@coffeecode.com` / `Mesero123!` | Mesero |
| `cajero@coffeecode.com` / `Cajero123!` | Cajero |
| `cocinero@coffeecode.com` / `Cocinero123!` | Cocinero |

</div>

<br/>

## 🧪 Testing

```bash
cd api
pytest app/tests/ -v          # 15 tests contra PostgreSQL real (transacción + rollback)
```

```bash
cd postman
npx newman run coffee-code.postman_collection.json   # 23 requests end-to-end
```

<br/>

## 📂 Estructura del repo

```
coffee-code/
├── api/                  # FastAPI — el núcleo
│   └── app/
│       ├── core/         # config, constantes de negocio
│       ├── data/         # modelos SQLAlchemy + conexión
│       ├── models/       # esquemas Pydantic
│       ├── routers/      # endpoints
│       ├── security/     # JWT + bcrypt
│       ├── services/     # lógica de negocio (máquina de estados, ventas...)
│       ├── websockets/   # ConnectionManager en tiempo real
│       └── tests/        # pytest
├── mobile/               # React Native + Expo (próximamente)
├── web-admin/            # Flask (próximamente)
├── postman/              # Colección validada con newman
└── docs/
```

<br/>

## 👥 Equipo

<div align="center">

| | |
|:--|:--|
| **Martinez Silvestre Coral** | Desarrollo |
| **Jimenez Vargas Diego** | Desarrollo |
| **Ledesma Ledesma Emiliano** | Desarrollo |
| **ISC Iván Isay Guerra López** | Asesor |

</div>

<br/>

<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:3B2412,100:6F4E37&height=120&section=footer" />

*Hecho con ☕ en UPQ*

</div>
