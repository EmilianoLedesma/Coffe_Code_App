# Mobile Fase 2b — Recetas (Cocina) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Cocinero manage a product's recipe (add/edit/remove ingredient lines, clear whole recipe) from the phone, closing the gap left out of Fase 2.

**Architecture:** Reuses `api/client.js` and Fase 2's `api/ingredientes.js::getIngredientes()`. Adds `api/recetas.js` and a new per-product `RecetaScreen.js` reached from `MenuScreen.js`.

**Tech Stack:** React Native (Expo), React Navigation 7, `fetch` via the shared `api/client.js`. No backend changes — `api/app/routers/recetas.py` already has full CRUD.

## Global Constraints

- Prerequisite: Fase 0 (infra) and Fase 2 (Cocina — provides `api/ingredientes.js`, `MenuScreen.js`, `App.js`'s current route list) are merged to `main` before this plan starts.
- Do NOT modify `api/client.js`, `auth/session.js`, `auth/AuthContext.js`, `api/pedidos_cocina.js`, `api/pedidos_caja.js`, any Mesero/Caja screen — out of scope.
- No axios, no socket.io, no new test framework — manual verification against the live Docker API, per `docs/superpowers/specs/2026-08-04-mobile-fase2b-recetas-design.md`.
- Seed credentials: `cocinero@coffeecode.com` / `Cocinero123!`.
- Backend endpoint shapes (already live, do not re-derive): `GET /producto_ingrediente?producto_id=X` → `RecetaOut[]` (`{id_producto, id_ingrediente, cantidad_requerida, ingrediente: {id, nombre, unidad, costo_unitario}}`); `POST /producto_ingrediente` body `{producto_id, ingrediente_id, cantidad}`; `PUT /producto_ingrediente/{producto_id}/{ingrediente_id}` body `{cantidad}`; `DELETE /producto_ingrediente/{producto_id}/{ingrediente_id}`; `DELETE /producto_ingrediente/producto/{producto_id}`.

---

### Task 1: `api/recetas.js`

**Files:**
- Create: `mobile/api/recetas.js`

**Interfaces:**
- Consumes: `request` from `api/client.js`.
- Produces: `getRecetasPorProducto(productoId): Promise<RecetaOut[]>`, `crearReceta({productoId, ingredienteId, cantidad}): Promise<RecetaOut>`, `actualizarReceta(productoId, ingredienteId, cantidad): Promise<RecetaOut>`, `eliminarReceta(productoId, ingredienteId): Promise<void>`, `eliminarRecetaCompleta(productoId): Promise<void>`. Consumed by Task 2's `RecetaScreen`.

- [ ] **Step 1: Create the file**

```js
import { request } from './client';

export function getRecetasPorProducto(productoId) {
  return request(`/producto_ingrediente?producto_id=${productoId}`);
}

export function crearReceta({ productoId, ingredienteId, cantidad }) {
  return request('/producto_ingrediente', {
    method: 'POST',
    body: {
      producto_id: productoId,
      ingrediente_id: ingredienteId,
      cantidad,
    },
  });
}

export function actualizarReceta(productoId, ingredienteId, cantidad) {
  return request(`/producto_ingrediente/${productoId}/${ingredienteId}`, {
    method: 'PUT',
    body: { cantidad },
  });
}

export function eliminarReceta(productoId, ingredienteId) {
  return request(`/producto_ingrediente/${productoId}/${ingredienteId}`, { method: 'DELETE' });
}

export function eliminarRecetaCompleta(productoId) {
  return request(`/producto_ingrediente/producto/${productoId}`, { method: 'DELETE' });
}
```

- [ ] **Step 2: Manual verification**

```bash
TOKEN=$(curl -s -X POST http://localhost:8010/auth/login -H "Content-Type: application/json" -d '{"correo_electronico":"cocinero@coffeecode.com","password":"Cocinero123!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s "http://localhost:8010/producto_ingrediente?producto_id=1" -H "Authorization: Bearer $TOKEN"
```

Expected: `200` with an array (may be empty if product 1 has no recipe yet — that's fine, just confirms the route/auth work).

- [ ] **Step 3: Commit**

```bash
git add mobile/api/recetas.js
git commit -m "feat(mobile): cliente API de recetas (producto_ingrediente)"
```

---

### Task 2: `RecetaScreen.js`

**Files:**
- Create: `mobile/screens/RecetaScreen.js`

**Interfaces:**
- Consumes: `getRecetasPorProducto`, `crearReceta`, `actualizarReceta`, `eliminarReceta`, `eliminarRecetaCompleta` from `api/recetas.js` (Task 1); `getIngredientes()` from `api/ingredientes.js` (Fase 2, already merged); `route.params.{productoId, productoNombre}` (produced by Task 3's `MenuScreen` link).
- Produces: nothing consumed by later tasks — this is the leaf screen.

- [ ] **Step 1: Create the file**

```js
import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import {
  getRecetasPorProducto,
  crearReceta,
  actualizarReceta,
  eliminarReceta,
  eliminarRecetaCompleta,
} from '../api/recetas';
import { getIngredientes } from '../api/ingredientes';
import { ApiError } from '../api/client';

export default function RecetaScreen({ route, navigation }) {
  const { productoId, productoNombre } = route.params;

  const [receta, setReceta] = useState([]);
  const [ingredientes, setIngredientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [ingredienteId, setIngredienteId] = useState(null);
  const [cantidad, setCantidad] = useState('');
  const [guardando, setGuardando] = useState(false);

  const [editandoId, setEditandoId] = useState(null);
  const [cantidadEditada, setCantidadEditada] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [recetaData, ingredientesData] = await Promise.all([
        getRecetasPorProducto(productoId),
        getIngredientes(),
      ]);
      setReceta(recetaData);
      setIngredientes(ingredientesData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, [productoId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const agregarIngrediente = async () => {
    if (!ingredienteId || !cantidad) {
      setError('Selecciona un ingrediente e ingresa la cantidad');
      return;
    }

    setGuardando(true);
    setError('');
    try {
      await crearReceta({ productoId, ingredienteId, cantidad: parseFloat(cantidad) });
      setIngredienteId(null);
      setCantidad('');
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo agregar el ingrediente');
    } finally {
      setGuardando(false);
    }
  };

  const iniciarEdicion = (linea) => {
    setEditandoId(linea.id_ingrediente);
    setCantidadEditada(String(linea.cantidad_requerida));
  };

  const guardarEdicion = async (idIngrediente) => {
    setError('');
    try {
      await actualizarReceta(productoId, idIngrediente, parseFloat(cantidadEditada));
      setEditandoId(null);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo actualizar la cantidad');
    }
  };

  const eliminarLinea = async (idIngrediente) => {
    setError('');
    try {
      await eliminarReceta(productoId, idIngrediente);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el ingrediente');
    }
  };

  const confirmarEliminarTodo = () => {
    Alert.alert(
      'Eliminar receta completa',
      `Esto quita todos los ingredientes de ${productoNombre}. ¿Continuar?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Eliminar', style: 'destructive', onPress: eliminarTodo },
      ]
    );
  };

  const eliminarTodo = async () => {
    setError('');
    try {
      await eliminarRecetaCompleta(productoId);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar la receta');
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Receta: {productoNombre}</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={receta}
        keyExtractor={(item) => item.id_ingrediente.toString()}
        ListEmptyComponent={<Text style={{ color: 'gray', marginBottom: 10 }}>Sin ingredientes aún</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.name}>{item.ingrediente.nombre}</Text>

            {editandoId === item.id_ingrediente ? (
              <View style={styles.row}>
                <TextInput
                  style={[styles.input, { flex: 1 }]}
                  keyboardType="numeric"
                  value={cantidadEditada}
                  onChangeText={setCantidadEditada}
                />
                <TouchableOpacity onPress={() => guardarEdicion(item.id_ingrediente)}>
                  <Text style={styles.guardar}>Guardar</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <>
                <Text>Cantidad: {item.cantidad_requerida} {item.ingrediente.unidad}</Text>
                <View style={styles.row}>
                  <TouchableOpacity onPress={() => iniciarEdicion(item)}>
                    <Text style={styles.editar}>Editar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => eliminarLinea(item.id_ingrediente)}>
                    <Text style={styles.eliminar}>Eliminar</Text>
                  </TouchableOpacity>
                </View>
              </>
            )}
          </View>
        )}
      />

      <Text style={styles.subtitle}>Agregar ingrediente</Text>

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
        placeholder="Cantidad requerida"
        value={cantidad}
        onChangeText={setCantidad}
        keyboardType="numeric"
        style={styles.input}
      />

      <TouchableOpacity style={styles.btn} onPress={agregarIngrediente} disabled={guardando}>
        <Text style={styles.btnText}>{guardando ? 'Guardando...' : 'Agregar'}</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.btnPeligro} onPress={confirmarEliminarTodo}>
        <Text style={styles.btnText}>Eliminar receta completa</Text>
      </TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 15, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 20, fontWeight: 'bold', marginBottom: 10 },
  subtitle: { marginTop: 10, fontWeight: 'bold' },
  error: { color: '#C0392B', marginBottom: 10 },
  card: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  name: { fontSize: 16, fontWeight: 'bold' },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8, alignItems: 'center' },
  editar: { color: '#2E1B0F', fontWeight: 'bold' },
  guardar: { color: 'green', fontWeight: 'bold', marginLeft: 10 },
  eliminar: { color: 'red' },
  input: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8, borderWidth: 1, borderColor: '#ddd' },
  categorias: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 10 },
  categoria: { padding: 8, marginRight: 8, marginBottom: 8, borderRadius: 8, borderWidth: 1, borderColor: '#ddd', color: 'gray' },
  categoriaSelected: { padding: 8, marginRight: 8, marginBottom: 8, borderRadius: 8, backgroundColor: '#2E1B0F', color: 'white' },
  btn: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8, marginBottom: 10 },
  btnPeligro: { backgroundColor: '#C0392B', padding: 12, borderRadius: 8, marginBottom: 10 },
  btnText: { color: 'white', textAlign: 'center', fontWeight: 'bold' },
});
```

- [ ] **Step 2: Commit**

```bash
git add mobile/screens/RecetaScreen.js
git commit -m "feat(mobile): RecetaScreen gestiona receta de un producto"
```

---

### Task 3: Wire navigation — `MenuScreen.js` link + `App.js` route

**Files:**
- Modify: `mobile/screens/MenuScreen.js` (Fase 2's file — adds one `TouchableOpacity` per product card, no other changes)
- Modify: `mobile/App.js` (adds one import + one route)

**Interfaces:**
- Consumes: `RecetaScreen` (Task 2).

- [ ] **Step 1: Add the "Ver receta" link in `mobile/screens/MenuScreen.js`**

Add `useNavigation` (or use the `navigation` prop already passed to `MenuScreen` if the component signature includes it — check the current signature first; Fase 2's `MenuScreen` is declared `export default function MenuScreen()` with no `navigation` prop, so add it):

Change the function signature from:

```js
export default function MenuScreen() {
```

to:

```js
export default function MenuScreen({ navigation }) {
```

Then, inside the `FlatList`'s `renderItem`, find the existing "Eliminar" `TouchableOpacity` for each product card and add a sibling link right after it:

```jsx
            <TouchableOpacity onPress={() => eliminar(item.id)}>
              <Text style={{ color: 'red', marginTop: 5 }}>Eliminar</Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={() => navigation.navigate('Receta', { productoId: item.id, productoNombre: item.nombre })}>
              <Text style={{ color: '#2E1B0F', marginTop: 5, fontWeight: 'bold' }}>Ver receta</Text>
            </TouchableOpacity>
```

- [ ] **Step 2: Register the route in `mobile/App.js`**

Add near the other screen imports:

```js
import RecetaScreen from './screens/RecetaScreen';
```

Add near the other `<Stack.Screen>` entries (any position after `CocinaDetalle`'s registration from Fase 2 is fine — order in the stack navigator doesn't affect behavior):

```jsx
        <Stack.Screen
          name="Receta"
          component={RecetaScreen}
        />
```

- [ ] **Step 3: Manual verification — full Recetas flow**

1. `docker compose up -d` in `api/` (confirm containers already running is fine).
2. `npx expo start` in `mobile/`, log in as `cocinero@coffeecode.com` / `Cocinero123!`.
3. Home → Cocina → Menú. Tap "Ver receta" on any product. Expected: navigates to `RecetaScreen` showing the product name, empty or existing recipe list.
4. Select an ingredient chip, enter cantidad `50`, tap "Agregar". Expected: new line appears in the list.
5. Confirm via `GET /producto_ingrediente?producto_id={id}` (Postman/curl) that the line exists with the right `cantidad_requerida`.
6. Tap "Editar" on that line, change the cantidad, tap "Guardar". Expected: updated value shown, confirmed via the same curl call.
7. Tap "Eliminar" on the line. Expected: line disappears, confirmed via curl (empty array or missing that ingredient).
8. Add 2 ingredients again, tap "Eliminar receta completa", confirm the native alert, confirm. Expected: list empties, confirmed via curl (`GET /producto_ingrediente?producto_id={id}` returns `[]`).

- [ ] **Step 4: Commit**

```bash
git add mobile/screens/MenuScreen.js mobile/App.js
git commit -m "feat(mobile): enlaza RecetaScreen desde MenuScreen"
```

---

## Fase 2b complete when

All 3 tasks committed, Task 3 Step 3's full manual verification passes against the live Docker API, including create/edit/delete-one/delete-all recipe operations.
