# Bloqueo de nombres duplicados (Ingredientes, Productos, Categorías, Recetas) — Diseño

## Contexto y problema

Las pruebas automatizadas contra la API (colecciones de Postman, agentes de la
prueba de fuego) crean entidades de prueba repetidamente. Como `Ingrediente`,
`Producto` y `Categoria` no tienen ninguna verificación de nombre duplicado al
crear, cada corrida deja registros nuevos con el mismo nombre (ej. múltiples
`"Leche"`), ensuciando la base de datos de desarrollo.

`Usuario` ya resuelve esto correctamente (`api/app/services/usuarios.py:17-23`
para crear, `api/app/services/usuarios.py:43-53` para actualizar): consulta si
ya existe un registro con ese correo antes de insertar/modificar, y responde
`409 Conflict` con un mensaje claro. Esta spec extiende el mismo patrón a
Ingredientes, Productos y Categorías (por `nombre`), y separa a Recetas
(por la pareja `producto_id`+`ingrediente_id`) porque su semántica es distinta.

Este cambio vive enteramente en la API (routers/services). No se modifica
ninguna colección de Postman ni el web-admin — las colecciones existentes que
hoy asumen que pueden recrear una entidad de prueba deberán, de ahora en
adelante, toparse con el 409 si la ejecutan dos veces sin limpiar; esto es
exactamente el comportamiento que se busca.

## Regla de duplicado (Ingredientes, Productos, Categorías)

Un nombre "ya existe" si hay **cualquier** fila (`activo=true` o `false`) cuyo
`nombre`, normalizado (recortado de espacios y en minúsculas), coincide con el
nombre normalizado que se intenta guardar. Ejemplo: `"Leche"`, `"leche "`,
`" LECHE"` se consideran el mismo nombre.

Se verifica en dos momentos:
- **Al crear** (`POST`): contra todas las filas existentes.
- **Al actualizar** (`PUT`), solo si el payload incluye un `nombre` distinto:
  contra todas las filas existentes **excluyendo la propia fila que se está
  editando** (mismo patrón que `usuarios.actualizar_usuario`, línea 46:
  `Usuario.id != usuario.id`).

En ambos casos, si hay coincidencia: `HTTPException(409, detail=f"Ya existe
un/una {entidad} con el nombre '{nombre}'")`. El texto exacto por entidad:

- Ingrediente: `"Ya existe un ingrediente con el nombre '{nombre}'"`
- Producto: `"Ya existe un producto con el nombre '{nombre}'"`
- Categoría: `"Ya existe una categoría con el nombre '{nombre}'"`

## Implementación

Cada router (`ingredientes.py`, `productos.py`, `categorias.py`) obtiene una
función privada local, ej.:

```python
def _verificar_nombre_no_duplicado(
    db: Session, modelo, nombre: str, excluir_id: int | None = None
) -> None:
    nombre_normalizado = nombre.strip().lower()
    consulta = db.query(modelo).filter(func.lower(func.trim(modelo.nombre)) == nombre_normalizado)
    if excluir_id is not None:
        consulta = consulta.filter(modelo.id != excluir_id)
    if consulta.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un ingrediente con el nombre '{nombre}'",  # texto ajustado por entidad
        )
```

(La función puede vivir duplicada y ajustada por archivo, igual que el resto
del código de estos routers no comparte helpers entre sí — no se introduce un
módulo compartido nuevo para esto, siguiendo el patrón existente donde cada
router es autocontenido.)

Se llama al inicio de `crear()` con el `nombre` del payload, y al inicio de
`actualizar()` únicamente si `"nombre" in datos.model_dump(exclude_unset=True)`.

## Recetas: reemplazar upsert por rechazo + nuevo endpoint de edición

Hoy `POST /producto_ingrediente` (`api/app/routers/recetas.py:32-62`) busca si
ya existe una receta para esa pareja `(producto_id, ingrediente_id)` y, si
existe, actualiza `cantidad_requerida` en silencio en vez de crear una fila
nueva (la pareja es la llave primaria compuesta, así que una fila duplicada
real es imposible a nivel de base de datos — pero el upsert silencioso oculta
que el llamador ya tenía una receta ahí).

Cambio:
- `POST /producto_ingrediente` deja de hacer upsert. Si la pareja ya existe,
  responde `409` con `"Ya existe una receta para este producto e ingrediente"`.
  Si no existe, crea la fila como hasta ahora (sin cambios en ese camino).
- Nuevo endpoint **`PUT /producto_ingrediente/{producto_id}/{ingrediente_id}`**
  con el mismo body que hoy acepta `POST` para `cantidad` (un
  `RecetaUpdate` nuevo con solo `cantidad: Decimal = Field(gt=0)`), que
  actualiza `cantidad_requerida` de una receta existente o responde `404` si
  no existe. Mismo rol de escritura (`_escritura`) que el resto del router.

El web-admin no depende del upsert (`web-admin/app/blueprints/recetas.py` solo
usa `crear_receta` para agregar un ingrediente nuevo a una receta, sin UI de
edición de cantidad existente) — no requiere ningún cambio para este fix.

## Fuera de alcance

- No se toca `Usuario` — ya está resuelto.
- No se agrega ningún endpoint de edición de cantidad en el web-admin (la API
  lo expone, pero construir la UI queda para otra sesión si se pide).
- No se modifica ninguna colección de Postman.
- No se introduce normalización Unicode más allá de `.strip().lower()` (sin
  manejo especial de acentos/ñ — `"Café"` y `"café"` se tratan como iguales
  por el `.lower()`, pero `"Café"` y `"Cafe"` seguirían siendo nombres
  distintos; no se pidió folding de acentos y agregarlo sería alcance extra).

## Pruebas

Casos nuevos en `api/app/tests/test_router_ingredientes.py`,
`test_router_productos.py`, `test_router_categorias.py`,
`test_router_recetas.py`:

- Crear con nombre exactamente duplicado → 409.
- Crear con variación de mayúsculas/espacios de un nombre existente → 409.
- Crear con un nombre que coincide con un registro **inactivo** → 409.
- Actualizar (`PUT`) renombrando hacia un nombre ya usado por otro registro → 409.
- Actualizar sin tocar `nombre` (u otro campo) → no dispara la verificación,
  sigue funcionando igual que hoy.
- Recetas: `POST` sobre una pareja ya existente → 409; `PUT` nuevo actualiza
  `cantidad_requerida` correctamente; `PUT` sobre una pareja inexistente → 404.
