# Mobile Fase 3b — Registrar Compra (Caja) — Design

Fecha: 2026-08-04

## Contexto

La spec original de wiring (`docs/superpowers/specs/2026-08-03-mobile-backend-wiring-design.md:106`)
esbozaba `POST /compras` como parte de Fase 3 (Caja), pero el plan de
implementación final (`docs/superpowers/plans/2026-08-03-mobile-fase3-caja.md`)
lo omitió — no encajaba en ninguna de las pantallas mock existentes (`CajaScreen`,
`PagoScreen`, `GastosScreen`), así que se dejó fuera sin decisión explícita.

`POST /compras` (`api/app/routers/caja.py::crear_compra`) ya existe, probado, y
hace dos cosas atómicamente: crea un `Gasto` real (`concepto=f"Compra de insumo: ..."`)
y sube `Ingrediente.stock_actual`. Es el flujo "correcto" para reflejar compras
de insumos con costo real — distinto del `PUT /ingredientes/{id}/stock` que usa
Cocina (Fase 2) para ajustes sin costo. Web-admin ya tiene un botón "Registrar
compra" equivalente en `ingredientes.html` (sesión 2026-07-04), pero corre bajo
un login de Administrador — nunca ejercita el rol Cajero real.

## Bloqueador encontrado y resuelto

`GET /ingredientes` (`api/app/routers/ingredientes.py:20`) está gateado a
`COCINERO, ADMINISTRADOR` — Cajero no tiene lectura. Sin esto, la app móvil de
Caja no puede construir un selector de ingredientes con el rol Cajero real
(confirmado también por la prueba de fuego, `progress.md` sesión 2026-07-04:
"`GET /ingredientes` bloqueado para Cajero").

**Decisión:** ampliar `_lectura` en `ingredientes.py` para incluir `CAJERO`.
`_escritura` (crear/editar/desactivar/eliminar/ajustar-stock) permanece
Cocinero/Administrador únicamente — sin cambio.

## Diseño

### Backend (cambio mínimo)

`api/app/routers/ingredientes.py:20`:

```python
_lectura = require_rol(RolNombre.COCINERO, RolNombre.CAJERO, RolNombre.ADMINISTRADOR)
```

Sin otros cambios — `_escritura` queda igual.

### Mobile

- **Nuevo:** `mobile/api/compras.js` — `crearCompra({ingredienteId, cantidad, monto}): Promise<CompraOut>` → `POST /compras`.
- **Reutiliza** `mobile/api/ingredientes.js::getIngredientes()` (creado por Fase 2, ya mergeado a `main` para cuando esta fase arranque) — sin duplicar el módulo, sin riesgo de conflicto de merge porque esta fase corre después, no en paralelo.
- **Modifica:** `mobile/screens/GastosScreen.js` — agrega una segunda tarjeta debajo del formulario de gasto existente:
  - Selector de ingrediente (chips, mismo patrón visual que el selector de categoría en `MenuScreen`), poblado con `getIngredientes()` al enfocar la pantalla.
  - Input `cantidad`, input `monto`.
  - Botón "Registrar compra" → `crearCompra(...)`.
  - Éxito: muestra `nuevo_stock` inline (ej. "Stock actualizado: 4500 ml"), sin navegación.
  - Error: mismo patrón inline (`ApiError.message`) que el resto de la pantalla.
- Sin pantalla nueva, sin ruta nueva en `App.js`.

## Manejo de errores

Igual que el resto de Fase 3: `ApiError.message` inline. Casos esperados del
backend: 404 si `ingrediente_id` no existe, 422 si `cantidad`/`monto` ≤ 0
(validación Pydantic `Field(gt=0)`).

## Verificación

Manual contra Docker real, sin test runner nuevo (mismo criterio que Fases 0-3):
login Cajero, Home → Caja → Gastos → sección "Comprar insumo", seleccionar
ingrediente, cantidad+monto válidos, confirmar `GET /ingredientes/{id}` refleja
el nuevo `stock_actual` y que aparece un `Gasto` nuevo vía `GET /caja/resumen`
(el total de gastos del día debe subir por `monto`).

## Alcance

Solo esta fase: rol ampliado en `ingredientes.py` + `compras.js` + cambios en
`GastosScreen.js`. No toca Cocina, Mesero, ni ninguna otra fase.
