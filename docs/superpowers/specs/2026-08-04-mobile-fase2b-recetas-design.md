# Mobile Fase 2b — Recetas (Cocina) — Design

Fecha: 2026-08-04

## Contexto

`CLAUDE.md` lista `POST /producto_ingrediente` (recetas) bajo los endpoints de
Cocina, y la spec original de wiring lo mencionaba para Fase 2, pero el plan
final (`docs/superpowers/plans/2026-08-03-mobile-fase2-cocina.md`) nunca lo
incluyó — no existía ninguna pantalla mock de recetas ni siquiera en el
prototipo original, así que no había nada que "reemplazar" y quedó fuera sin
decisión explícita. El backend (`api/app/routers/recetas.py`) ya tiene el CRUD
completo: listar por producto, crear, actualizar cantidad, eliminar una línea,
eliminar la receta completa de un producto.

## Diseño

Sin cambios de backend — solo wiring móvil nuevo.

### Mobile

- **Nuevo:** `mobile/api/recetas.js`:
  - `getRecetasPorProducto(productoId)` → `GET /producto_ingrediente?producto_id=X`
  - `crearReceta({productoId, ingredienteId, cantidad})` → `POST /producto_ingrediente`
  - `actualizarReceta(productoId, ingredienteId, cantidad)` → `PUT /producto_ingrediente/{producto_id}/{ingrediente_id}`
  - `eliminarReceta(productoId, ingredienteId)` → `DELETE /producto_ingrediente/{producto_id}/{ingrediente_id}`
  - `eliminarRecetaCompleta(productoId)` → `DELETE /producto_ingrediente/producto/{producto_id}`

- **Nuevo:** `mobile/screens/RecetaScreen.js` — recibe `route.params.{productoId, productoNombre}`:
  - Header con el nombre del producto.
  - Lista de líneas de receta actuales (`ingrediente.nombre`, `cantidad_requerida`, `unidad`), cada una con "Editar" (input de cantidad inline) y "Eliminar".
  - Sección inferior: agregar ingrediente — selector de chips (mismo patrón visual que el selector de categoría en `MenuScreen`, poblado con `getIngredientes()` — reutiliza el módulo de Fase 2, sin duplicar), input de cantidad, botón "Agregar".
  - Botón de pie "Eliminar receta completa" con confirmación (acción destructiva — usar un segundo tap o `Alert.alert` de confirmación nativo, no ejecutar en el primer tap).

- **Modifica:** `mobile/screens/MenuScreen.js` (archivo de Fase 2) — cada tarjeta de producto gana un enlace "Ver receta" → `navigation.navigate('Receta', { productoId: item.id, productoNombre: item.nombre })`.

- **Modifica:** `mobile/App.js` — agrega `import RecetaScreen` + `<Stack.Screen name="Receta" component={RecetaScreen} />`.

## Manejo de errores

Mismo patrón que el resto de Fase 2: `ApiError.message` inline. Casos
esperados del backend: 409 si la pareja producto+ingrediente ya existe al
crear, 404 si producto/ingrediente/receta no existen.

## Verificación

Manual contra Docker real, sin test runner nuevo (mismo criterio que fases
anteriores): login Cocinero, Home → Cocina → Menú → tap "Ver receta" en un
producto, agregar un ingrediente con cantidad, confirmar vía
`GET /producto_ingrediente?producto_id=X` (Postman/curl) que aparece. Editar
la cantidad, confirmar el cambio. Eliminar la línea, confirmar que desaparece.

## Alcance

Solo esta fase: `api/recetas.js` + `RecetaScreen.js` nuevos, cambios menores en
`MenuScreen.js` y `App.js` (ambos ya existentes de Fase 2, mergeados antes de
que esta fase arranque). No toca Mesero, Caja, ni ninguna otra fase.
