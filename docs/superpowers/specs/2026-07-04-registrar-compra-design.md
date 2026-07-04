# Registrar compra de insumo (web-admin) — Diseño

## Contexto y problema

El endpoint `POST /compras` ya existe en la API (`api/app/routers/caja.py::crear_compra` →
`api/app/services/gastos.py::registrar_compra`) y hace correctamente dos cosas en una
transacción: crea un `Gasto` con concepto y monto real, y sube `ingrediente.stock_actual`.

El web-admin no tiene ninguna página que llame a este endpoint. El único control que existe
para subir stock desde el panel es "Ajustar stock" (`PUT /ingredientes/{id}/stock`), que es un
ajuste delta puro sin costo asociado — no crea ningún registro en `GASTOS`. Por eso, sin
importar cuánto stock se agregue desde el panel, los gastos nunca suben: el único camino
disponible en la UI no pasa por el flujo de gasto real.

Esta spec cubre exclusivamente agregar la vista de "Registrar compra" al web-admin. No hay
cambios de API, de base de datos, ni de migraciones — el backend ya soporta esto.

## Semántica: dos acciones separadas, cada una con su propósito

- **Ajustar stock** (sin cambios): corrección sin costo — mermas, conteo físico, producto
  dañado. Sigue llamando a `PUT /ingredientes/{id}/stock`, delta puro, puede ser negativo.
- **Registrar compra** (nueva): compra real de insumo. Sube stock y crea un gasto en una sola
  acción, llamando a `POST /compras`. Solo acepta cantidades y montos positivos (ya validado
  por la API con `Field(gt=0)` en `CompraCreate`).

`costo_unitario` del ingrediente queda fuera de alcance: sigue siendo un valor de referencia
editado a mano vía `PUT /ingredientes/{id}` (ya implementado en el sprint anterior). Registrar
una compra no recalcula `costo_unitario` automáticamente.

## Ubicación en la UI

Dentro de la página existente `web-admin/app/templates/ingredientes.html`, un botón
"Registrar compra" por fila, junto al botón "Ajustar stock" ya existente. Abre un modal con el
mismo patrón Alpine.js que `modalStock` (`x-data`, `modalCompra` en vez de reutilizar
`modalStock` para no mezclar los dos formularios).

Campos del modal:
- Ingrediente: preseleccionado desde la fila (nombre visible, no editable, igual que en
  "Ajustar stock").
- `cantidad`: número, a sumar al stock actual.
- `monto`: número, costo total de la compra (se registra como gasto).

Al enviar exitosamente: redirige a la lista de ingredientes con flash de éxito mostrando el
nuevo stock (ej. "Compra registrada. Nuevo stock de Leche: 10360 ml."). Errores (ingrediente no
encontrado, campos inválidos) se manejan igual que el resto de acciones del panel — flash de
error y redirect de vuelta a la lista.

## Piezas a construir

1. **`web-admin/app/api_client.py`** — nueva función `registrar_compra(base_url, token,
   ingrediente_id, cantidad, monto) -> dict`, sigue el mismo patrón que
   `ajustar_stock_ingrediente` (llama a `_request("POST", base_url, "/compras", ...)`, propaga
   `ApiError` en fallos).
2. **`web-admin/app/blueprints/ingredientes.py`** — nueva ruta `POST
   /ingredientes/<int:ingrediente_id>/comprar`, valida `cantidad`/`monto` del form (positivos,
   parseable a Decimal/float), llama a `api_client.registrar_compra`, maneja `ApiError` con
   flash + redirect (mismo patrón que la ruta de `ajustar_stock` existente).
3. **`web-admin/app/templates/ingredientes.html`** — botón "Registrar compra" por fila +
   modal `modalCompra` (form con `ingrediente_id` implícito en la action URL, inputs `cantidad`
   y `monto`).
4. **Tests** (`web-admin/tests/test_ingredientes.py` o archivo equivalente ya existente):
   - Compra exitosa: verifica que se llama a `POST /compras` con el payload correcto y que la
     respuesta redirige con flash de éxito.
   - Ingrediente inexistente: la API devuelve 404, la ruta debe mostrar flash de error sin
     crashear.
   - Validación de campos: cantidad/monto no positivos o no numéricos deben rechazarse antes de
     llamar a la API (o dejar que la API los rechace y manejar el error correctamente — a
     definir en el plan de implementación cuál capa valida primero).
5. **Postman**: nueva request en la colección para `POST /ingredientes/<id>/comprar` (ruta del
   web-admin). Nota: `POST /compras` de la API ya está cubierto en Postman desde la sesión
   anterior — no requiere cambios ahí.

## Fuera de alcance (explícitamente, para esta spec)

- Recalcular `costo_unitario` como promedio ponderado al comprar.
- Página/listado histórico de compras o de gastos individuales (hoy los gastos solo se ven
  agregados en el dashboard financiero y el corte diario; esta spec no agrega una vista de
  detalle).
- Cualquier cambio a `PUT /ingredientes/{id}/stock` ("Ajustar stock") — permanece intacto.
