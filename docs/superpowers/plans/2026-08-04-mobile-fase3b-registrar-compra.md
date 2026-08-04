# Mobile Fase 3b — Registrar Compra (Caja) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Cajero register a real ingredient purchase (`POST /compras`) from the phone — creates a real `Gasto` and increments `Ingrediente.stock_actual` atomically, closing the gap left out of Fase 3.

**Architecture:** Widen one backend role gate (`GET /ingredientes` read access), add one small mobile API module (`api/compras.js`), extend `GastosScreen` with a second card reusing Fase 2's `api/ingredientes.js::getIngredientes()` for the picker.

**Tech Stack:** FastAPI (one-line role change), React Native (Expo), `fetch` via the shared `api/client.js`.

## Global Constraints

- Prerequisite: Fase 0 (infra), Fase 2 (Cocina — provides `api/ingredientes.js`), and Fase 3 (Caja — provides `GastosScreen.js`) are all merged to `main` before this plan starts.
- Do NOT modify `api/client.js`, `auth/session.js`, `auth/AuthContext.js`, `api/pedidos.js`, `api/pedidos_cocina.js`, `api/pedidos_caja.js` — out of scope.
- Backend write access to ingredientes (`_escritura` in `ingredientes.py`) stays Cocinero/Administrador only — only the read gate (`_lectura`) widens.
- No axios, no socket.io, no new test framework — manual verification against the live Docker API, per `docs/superpowers/specs/2026-08-04-mobile-fase3b-registrar-compra-design.md`.
- Seed credentials: `cajero@coffeecode.com` / `Cajero123!`.

---

### Task 1: Backend — widen ingredientes read access to Cajero

**Files:**
- Modify: `api/app/routers/ingredientes.py:20`
- Test: `api/app/tests/test_router_ingredientes.py` (new test)

**Interfaces:**
- Produces: `GET /ingredientes` and `GET /ingredientes/{id}` now accessible to Cajero (in addition to Cocinero/Administrador). Consumed by Task 3's mobile picker.

- [ ] **Step 1: Read the current role gate**

Confirm current state at `api/app/routers/ingredientes.py:20-21`:

```python
_lectura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)
_escritura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)
```

- [ ] **Step 2: Write the failing test**

Add to `api/app/tests/test_router_ingredientes.py` (create the file if it doesn't exist — check first, most routers already have one; if `test_router_ingredientes.py` doesn't exist, look at `api/app/tests/test_router_productos.py` for the fixture/client pattern used across the test suite and mirror it):

```python
def test_cajero_puede_listar_ingredientes(client, token_cajero):
    response = client.get("/ingredientes", headers={"Authorization": f"Bearer {token_cajero}"})
    assert response.status_code == 200


def test_cajero_no_puede_crear_ingrediente(client, token_cajero):
    response = client.post(
        "/ingredientes",
        json={"nombre": "Test Cajero Bloqueado", "unidad": "g", "stock_minimo": 1, "costo_unitario": 1},
        headers={"Authorization": f"Bearer {token_cajero}"},
    )
    assert response.status_code == 403
```

If the test file already has a `token_cajero` fixture (check `conftest.py` or the top of an existing test file like `test_router_caja.py` — Fase 3's `/ventas`/`/gastos`/`/compras` endpoints already require Cajero auth, so a fixture almost certainly exists), reuse it. Do not create a duplicate fixture.

- [ ] **Step 3: Run tests to verify the first one fails**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_ingredientes.py -v -k cajero`
Expected: `test_cajero_puede_listar_ingredientes` FAILS with 403 (current gate blocks Cajero), `test_cajero_no_puede_crear_ingrediente` PASSES already (write is already blocked).

- [ ] **Step 4: Widen the read gate**

In `api/app/routers/ingredientes.py:20`, change:

```python
_lectura = require_rol(RolNombre.COCINERO, RolNombre.ADMINISTRADOR)
```

to:

```python
_lectura = require_rol(RolNombre.COCINERO, RolNombre.CAJERO, RolNombre.ADMINISTRADOR)
```

Leave line 21 (`_escritura`) untouched.

- [ ] **Step 5: Run tests to verify both pass**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest app/tests/test_router_ingredientes.py -v -k cajero`
Expected: both PASS.

- [ ] **Step 6: Run the full API test suite to confirm no regression**

Run: `cd api && ./.venv/Scripts/python.exe -m pytest -v`
Expected: all pass, same count as before plus the 2 new tests.

- [ ] **Step 7: Commit**

```bash
git add api/app/routers/ingredientes.py api/app/tests/test_router_ingredientes.py
git commit -m "feat(api): Cajero puede leer ingredientes (necesario para registrar compras)"
```

---

### Task 2: Rebuild API container and verify live

**Files:** None (operational step — no code changes)

**Interfaces:** None.

- [ ] **Step 1: Rebuild and restart the API container**

```bash
cd api
docker compose build coffee_code_api
docker compose up -d coffee_code_api
```

- [ ] **Step 2: Verify against the live container**

```bash
TOKEN=$(curl -s -X POST http://localhost:8010/auth/login -H "Content-Type: application/json" -d '{"correo_electronico":"cajero@coffeecode.com","password":"Cajero123!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s http://localhost:8010/ingredientes -H "Authorization: Bearer $TOKEN"
```

Expected: `200` with a JSON array of ingredientes (not `403`).

- [ ] **Step 3: Commit (no-op if nothing changed, skip if already committed in Task 1)**

Nothing to commit here — this task is verification only.

---

### Task 3: Mobile — `api/compras.js` + GastosScreen "Comprar insumo" section

**Files:**
- Create: `mobile/api/compras.js`
- Modify: `mobile/screens/GastosScreen.js` (adds a second card below the existing gasto form — does not remove or rewrite the existing gasto logic)

**Interfaces:**
- Consumes: `request` from `api/client.js`, `getIngredientes()` from `api/ingredientes.js` (Fase 2, already merged).
- Produces: `crearCompra({ingredienteId, cantidad, monto}): Promise<{gasto, ingrediente_id, nuevo_stock}>`.

- [ ] **Step 1: Create `mobile/api/compras.js`**

```js
import { request } from './client';

export function crearCompra({ ingredienteId, cantidad, monto }) {
  return request('/compras', {
    method: 'POST',
    body: {
      ingrediente_id: ingredienteId,
      cantidad,
      monto,
    },
  });
}
```

- [ ] **Step 2: Add imports and state to `mobile/screens/GastosScreen.js`**

At the top of the file, add to the existing imports:

```js
import { getIngredientes } from '../api/ingredientes';
import { crearCompra } from '../api/compras';
```

Inside the `GastosScreen` component, add new state alongside the existing `descripcion`/`monto`/`gastosSesion`/`totalPeriodo` state:

```js
  const [ingredientes, setIngredientes] = useState([]);
  const [ingredienteId, setIngredienteId] = useState(null);
  const [cantidadCompra, setCantidadCompra] = useState('');
  const [montoCompra, setMontoCompra] = useState('');
  const [comprando, setComprando] = useState(false);
  const [resultadoCompra, setResultadoCompra] = useState(null);
```

- [ ] **Step 3: Load ingredientes alongside the existing resumen fetch**

Find the existing `cargarResumen` `useCallback` and the `useFocusEffect` that calls it. Add a sibling loader and call both in the same effect:

```js
  const cargarIngredientes = useCallback(async () => {
    try {
      setIngredientes(await getIngredientes());
    } catch (err) {
      setIngredientes([]);
    }
  }, []);
```

Change the existing:

```js
  useFocusEffect(
    useCallback(() => {
      cargarResumen();
    }, [cargarResumen])
  );
```

to:

```js
  useFocusEffect(
    useCallback(() => {
      cargarResumen();
      cargarIngredientes();
    }, [cargarResumen, cargarIngredientes])
  );
```

- [ ] **Step 4: Add the `registrarCompra` handler**

Add alongside the existing `agregarGasto` function:

```js
  const registrarCompra = async () => {
    if (!ingredienteId || !cantidadCompra || !montoCompra) {
      setError('Selecciona un ingrediente y completa cantidad y monto');
      return;
    }

    setComprando(true);
    setError('');
    setResultadoCompra(null);
    try {
      const resultado = await crearCompra({
        ingredienteId,
        cantidad: parseFloat(cantidadCompra),
        monto: parseFloat(montoCompra),
      });
      setResultadoCompra(resultado);
      setCantidadCompra('');
      setMontoCompra('');
      await cargarResumen();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar la compra');
    } finally {
      setComprando(false);
    }
  };
```

- [ ] **Step 5: Add the JSX section**

Insert this new card between the existing gasto-form `<View style={styles.card}>` block and the `<View style={styles.totalBox}>` block:

```jsx
      <View style={styles.card}>

        <Text style={{ fontWeight: 'bold', marginBottom: 10 }}>Comprar insumo</Text>

        <View style={styles.categorias}>
          {ingredientes.map((ing) => (
            <TouchableOpacity key={ing.id} onPress={() => setIngredienteId(ing.id)}>
              <Text style={ingredienteId === ing.id ? styles.categoriaSelected : styles.categoria}>
                {ing.nombre}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <TextInput
          placeholder="Cantidad"
          value={cantidadCompra}
          onChangeText={setCantidadCompra}
          keyboardType="numeric"
          style={styles.input}
        />

        <TextInput
          placeholder="Monto"
          value={montoCompra}
          onChangeText={setMontoCompra}
          keyboardType="numeric"
          style={styles.input}
        />

        {resultadoCompra ? (
          <Text style={{ color: 'green', marginBottom: 10 }}>
            Compra registrada. Nuevo stock: {resultadoCompra.nuevo_stock}
          </Text>
        ) : null}

        <TouchableOpacity style={styles.btnAgregar} onPress={registrarCompra} disabled={comprando}>
          <Text style={styles.btnText}>{comprando ? 'Registrando...' : 'Registrar compra'}</Text>
        </TouchableOpacity>

      </View>
```

- [ ] **Step 6: Add the two missing styles**

Add to the existing `StyleSheet.create` block in `GastosScreen.js` (the `categorias`/`categoria`/`categoriaSelected` pattern already exists in `MenuScreen.js` — copy those three style objects verbatim, they are not yet in `GastosScreen.js`'s stylesheet):

```js
  categorias: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 10 },
  categoria: { padding: 8, marginRight: 8, marginBottom: 8, borderRadius: 8, borderWidth: 1, borderColor: '#ddd', color: 'gray' },
  categoriaSelected: { padding: 8, marginRight: 8, marginBottom: 8, borderRadius: 8, backgroundColor: '#2E1B0F', color: 'white' },
```

- [ ] **Step 7: Manual verification**

1. Confirm Task 1/2's backend change is live (`docker compose up -d coffee_code_api` already done).
2. `npx expo start` in `mobile/`, log in as `cajero@coffeecode.com` / `Cajero123!`.
3. Home → Caja → "Gastos y cuentas". Expected: a "Comprar insumo" section appears below the existing gasto form, with chips for each real ingredient (Leche, Café molido, etc. from seed).
4. Select an ingredient, enter cantidad `500`, monto `50`, tap "Registrar compra". Expected: success text "Compra registrada. Nuevo stock: ..." appears.
5. Confirm via `GET /ingredientes/{id}` (Postman/curl) that `stock_actual` increased by exactly `500`.
6. Confirm via `GET /caja/resumen?desde=<today-midnight-ISO>` that `total_gastos` increased by `50`.
7. Try submitting with cantidad `0`: expected inline error (backend 422), no crash.

- [ ] **Step 8: Commit**

```bash
git add mobile/api/compras.js mobile/screens/GastosScreen.js
git commit -m "feat(mobile): Caja registra compras de insumo reales via POST /compras"
```

---

## Fase 3b complete when

Both tasks committed, Task 3 Step 7's full manual verification passes against the live Docker API — including the atomic stock+gasto increment and the Cajero-role read confirmation from Task 2.
