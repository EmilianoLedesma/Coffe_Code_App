# Mobile Fase 2 — Cocina Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Cocina flow (cola de pedidos FIFO → cambiar estatus → gestión de menú → gestión de inventario) end-to-end against the real FastAPI backend.

**Architecture:** Reuses `api/client.js`, `auth/session.js`, `auth/AuthContext.js` from Fase 0 (already merged to `main` — do not modify those three files). Adds Cocina-only API modules and rewrites the four Cocina screens (currently pure mock `useState` arrays) to call the real endpoints.

**Tech Stack:** React Native (Expo), React Navigation 7, `fetch` via the shared `api/client.js`.

## Global Constraints

- Prerequisite: Fase 0 (`docs/superpowers/plans/2026-08-03-mobile-fase0-infra-mesero.md`) is merged to `main` before this plan starts — `api/client.js`, `auth/session.js`, `auth/AuthContext.js`, `config.js`, `app.config.js` already exist.
- **Isolation rule:** this plan creates `api/pedidos_cocina.js` as a NEW file for pedido-queue calls rather than modifying the shared `api/pedidos.js` from Fase 0 — Fase 3 (Caja) also needs pedido reads and runs in a parallel worktree; two phases editing the same file would conflict on merge. Minor duplication of a couple of `request()` wrapper calls is the accepted tradeoff for merge safety.
- This plan touches ONLY: `api/categorias.js` (new), `api/productos.js` (extends Fase 0's read-only version with write methods — Fase 3 never touches this file, safe), `api/ingredientes.js` (new), `api/pedidos_cocina.js` (new), `screens/CocinaScreen.js`, `screens/ColaPedidosScreen.js`, `screens/MenuScreen.js`, `screens/InventarioScreen.js`, `screens/CocinaDetalleScreen.js` (new), `App.js` (adds one route). It must NOT touch any Caja screen/file or `api/pedidos.js`.
- No axios, no socket.io, no new test framework — manual verification against the live Docker API, per `docs/superpowers/specs/2026-08-03-mobile-backend-wiring-design.md`.
- Seed credentials: `cocinero@coffeecode.com` / `Cocinero123!`.

---

### Task 1: Menu management — real CRUD on `/productos` + `/categorias`

**Files:**
- Create: `mobile/api/categorias.js`
- Modify: `mobile/api/productos.js` (Fase 0 only defined `getProductos()`; this task adds `createProducto`/`updateProducto`/`deleteProducto` — additive, no existing export changes)
- Modify: `mobile/screens/MenuScreen.js` (full replacement — mock in-memory product list replaced with real API calls)

**Interfaces:**
- Consumes: `request` from `api/client.js`.
- Produces: `getCategorias(): Promise<Array<{id, nombre, descripcion, activo}>>`. `productos.js` gains `createProducto(payload)`, `updateProducto(id, payload)`, `deleteProducto(id): Promise<{eliminado, mensaje}>`.

- [ ] **Step 1: Create `mobile/api/categorias.js`**

```js
import { request } from './client';

export function getCategorias() {
  return request('/categorias');
}
```

- [ ] **Step 2: Extend `mobile/api/productos.js`**

Append to the existing file (do not remove `getProductos`):

```js
export function createProducto({ nombre, descripcion, precioVenta, idCategoria }) {
  return request('/productos', {
    method: 'POST',
    body: {
      nombre,
      descripcion: descripcion || null,
      precio_venta: precioVenta,
      disponible: true,
      activo: true,
      id_categoria: idCategoria,
    },
  });
}

export function updateProducto(id, payload) {
  return request(`/productos/${id}`, { method: 'PUT', body: payload });
}

export function deleteProducto(id) {
  return request(`/productos/${id}`, { method: 'DELETE' });
}
```

- [ ] **Step 3: Replace `mobile/screens/MenuScreen.js` entirely**

```js
import React, { useCallback, useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getProductos, createProducto, deleteProducto } from '../api/productos';
import { getCategorias } from '../api/categorias';
import { ApiError } from '../api/client';

export default function MenuScreen() {
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [categoriaId, setCategoriaId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [nombre, setNombre] = useState('');
  const [precio, setPrecio] = useState('');
  const [descripcion, setDescripcion] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [prods, cats] = await Promise.all([getProductos(), getCategorias()]);
      setProductos(prods);
      setCategorias(cats);
      if (cats.length > 0 && categoriaId === null) setCategoriaId(cats[0].id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, [categoriaId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const agregarProducto = async () => {
    if (!nombre.trim() || !precio || !categoriaId) {
      setError('Completa nombre, precio y categoría');
      return;
    }

    setError('');
    try {
      await createProducto({
        nombre: nombre.trim(),
        descripcion: descripcion.trim(),
        precioVenta: parseFloat(precio),
        idCategoria: categoriaId,
      });
      setNombre('');
      setPrecio('');
      setDescripcion('');
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear el producto');
    }
  };

  const eliminar = async (id) => {
    setError('');
    try {
      await deleteProducto(id);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el producto');
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

      <Text style={styles.title}>Gestión de Menú</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TextInput placeholder="Nombre" value={nombre} onChangeText={setNombre} style={styles.input} />
      <TextInput placeholder="Precio" value={precio} onChangeText={setPrecio} keyboardType="numeric" style={styles.input} />
      <TextInput placeholder="Descripción" value={descripcion} onChangeText={setDescripcion} style={styles.input} />

      <View style={styles.categorias}>
        {categorias.map((cat) => (
          <TouchableOpacity key={cat.id} onPress={() => setCategoriaId(cat.id)}>
            <Text style={categoriaId === cat.id ? styles.categoriaSelected : styles.categoria}>
              {cat.nombre}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity style={styles.btn} onPress={agregarProducto}>
        <Text style={styles.btnText}>Agregar producto</Text>
      </TouchableOpacity>

      <FlatList
        data={productos}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.name}>{item.nombre}</Text>
            <Text>${item.precio_venta}</Text>
            <Text>{item.categoria.nombre}</Text>

            <TouchableOpacity onPress={() => eliminar(item.id)}>
              <Text style={{ color: 'red', marginTop: 5 }}>Eliminar</Text>
            </TouchableOpacity>
          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 15, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  input: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  categorias: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 10 },
  categoria: { padding: 8, marginRight: 8, marginBottom: 8, borderRadius: 8, borderWidth: 1, borderColor: '#ddd', color: 'gray' },
  categoriaSelected: { padding: 8, marginRight: 8, marginBottom: 8, borderRadius: 8, backgroundColor: '#2E1B0F', color: 'white' },
  btn: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8, marginBottom: 10 },
  btnText: { color: 'white', textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  name: { fontSize: 16, fontWeight: 'bold' }
});
```

- [ ] **Step 4: Manual verification**

Log in as `cocinero@coffeecode.com`, navigate Home → Cocina → Menú. Expected: real seed products list (Café Americano, Espresso, etc.), category chips populated from `GET /categorias`. Create a test product, confirm it appears via `GET /productos` in Postman. Delete it, confirm it's gone (or deactivated if it somehow already has order history — check via `GET /productos?incluir_inactivos=true`).

- [ ] **Step 5: Commit**

```bash
git add mobile/api/categorias.js mobile/api/productos.js mobile/screens/MenuScreen.js
git commit -m "feat(mobile): MenuScreen CRUD real de productos y categorias"
```

---

### Task 2: Inventario screen — real CRUD on `/ingredientes`

**Files:**
- Create: `mobile/api/ingredientes.js`
- Modify: `mobile/screens/InventarioScreen.js` (full replacement — mock stock +1/-1 buttons replaced with real stock-delta calls)

**Interfaces:**
- Consumes: `request` from `api/client.js`.
- Produces: `getIngredientes(): Promise<Array<{id, nombre, unidad, stock_actual, stock_minimo, costo_unitario, activo}>>`, `createIngrediente(payload)`, `ajustarStock(id, cantidad)`, `deleteIngrediente(id)`.

- [ ] **Step 1: Create `mobile/api/ingredientes.js`**

```js
import { request } from './client';

export function getIngredientes() {
  return request('/ingredientes');
}

export function createIngrediente({ nombre, unidad, stockMinimo, costoUnitario }) {
  return request('/ingredientes', {
    method: 'POST',
    body: {
      nombre,
      unidad,
      stock_actual: 0,
      stock_minimo: stockMinimo,
      costo_unitario: costoUnitario,
      activo: true,
    },
  });
}

export function ajustarStock(id, cantidad) {
  return request(`/ingredientes/${id}/stock`, {
    method: 'PUT',
    body: { cantidad },
  });
}

export function deleteIngrediente(id) {
  return request(`/ingredientes/${id}`, { method: 'DELETE' });
}
```

- [ ] **Step 2: Replace `mobile/screens/InventarioScreen.js` entirely**

```js
import React, { useCallback, useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getIngredientes, createIngrediente, ajustarStock, deleteIngrediente } from '../api/ingredientes';
import { ApiError } from '../api/client';

export default function InventarioScreen() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [nombre, setNombre] = useState('');
  const [unidad, setUnidad] = useState('');
  const [stockMinimo, setStockMinimo] = useState('');
  const [costoUnitario, setCostoUnitario] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await getIngredientes());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const agregar = async () => {
    if (!nombre.trim() || !unidad.trim() || !stockMinimo || !costoUnitario) {
      setError('Completa nombre, unidad, stock mínimo y costo unitario');
      return;
    }

    setError('');
    try {
      await createIngrediente({
        nombre: nombre.trim(),
        unidad: unidad.trim(),
        stockMinimo: parseFloat(stockMinimo),
        costoUnitario: parseFloat(costoUnitario),
      });
      setNombre('');
      setUnidad('');
      setStockMinimo('');
      setCostoUnitario('');
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear el ingrediente');
    }
  };

  const subir = async (id) => {
    setError('');
    try {
      await ajustarStock(id, 1);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo ajustar el stock');
    }
  };

  const bajar = async (id) => {
    setError('');
    try {
      await ajustarStock(id, -1);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo ajustar el stock');
    }
  };

  const eliminar = async (id) => {
    setError('');
    try {
      await deleteIngrediente(id);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el ingrediente');
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

      <Text style={styles.title}>Inventario</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TextInput placeholder="Nombre" value={nombre} onChangeText={setNombre} style={styles.input} />
      <TextInput placeholder="Unidad (g, ml, u)" value={unidad} onChangeText={setUnidad} style={styles.input} />
      <TextInput placeholder="Stock mínimo" value={stockMinimo} onChangeText={setStockMinimo} keyboardType="numeric" style={styles.input} />
      <TextInput placeholder="Costo unitario" value={costoUnitario} onChangeText={setCostoUnitario} keyboardType="numeric" style={styles.input} />

      <TouchableOpacity style={styles.btn} onPress={agregar}>
        <Text style={styles.btnText}>Agregar ingrediente</Text>
      </TouchableOpacity>

      <FlatList
        data={items}
        keyExtractor={(i) => i.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.card}>

            <Text style={styles.name}>{item.nombre}</Text>
            <Text>Stock: {item.stock_actual} {item.unidad}</Text>
            <Text style={item.stock_actual < item.stock_minimo ? styles.bajo : null}>
              Mínimo: {item.stock_minimo} {item.unidad}
            </Text>

            <View style={styles.row}>
              <TouchableOpacity onPress={() => subir(item.id)}>
                <Text style={styles.plus}>+1</Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={() => bajar(item.id)}>
                <Text style={styles.minus}>-1</Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={() => eliminar(item.id)}>
                <Text style={styles.delete}>Eliminar</Text>
              </TouchableOpacity>
            </View>

          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 15, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  input: { backgroundColor: 'white', padding: 10, marginBottom: 8, borderRadius: 8 },
  btn: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8, marginBottom: 10 },
  btnText: { color: 'white', textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  name: { fontSize: 16, fontWeight: 'bold' },
  bajo: { color: '#C0392B', fontWeight: 'bold' },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  plus: { color: 'green', fontSize: 16 },
  minus: { color: 'orange', fontSize: 16 },
  delete: { color: 'red' }
});
```

- [ ] **Step 3: Manual verification**

Log in as `cocinero@coffeecode.com`, Home → Cocina → Inventario. Expected: real ingredient list from seed (Leche, Café molido, etc.) with real `stock_actual`. Tap "+1" on one, confirm via `GET /ingredientes/{id}` the stock increased by exactly 1. Try to push one below 0 with repeated "-1": expected an inline error once the API returns 409, not a crash.

- [ ] **Step 4: Commit**

```bash
git add mobile/api/ingredientes.js mobile/screens/InventarioScreen.js
git commit -m "feat(mobile): InventarioScreen CRUD real de ingredientes"
```

---

### Task 3: Cola de pedidos — FIFO real + cambio de estatus

**Files:**
- Create: `mobile/api/pedidos_cocina.js`
- Create: `mobile/screens/CocinaDetalleScreen.js`
- Modify: `mobile/screens/ColaPedidosScreen.js` (full replacement — mock 3-item array replaced with real `GET /pedidos?estado=Pendiente`; also fixes the Fase 0 compatibility shim that pointed here at Mesero's read-only `Detalle` screen)
- Modify: `mobile/screens/CocinaScreen.js:14` (replace the hardcoded `"Pedidos en espera: 3"` text with a real count fetched on mount)
- Modify: `mobile/App.js` (add `CocinaDetalleScreen` import + route)

**Interfaces:**
- Consumes: `request` from `api/client.js`.
- Produces: `getColaPendientes(): Promise<PedidoOut[]>`, `cambiarEstadoPedido(id, estatus): Promise<PedidoOut>` (estatus ∈ `'En preparación' | 'Listo'`, matching the backend's state machine for the Cocina role).

- [ ] **Step 1: Create `mobile/api/pedidos_cocina.js`**

```js
import { request } from './client';

export function getColaPendientes() {
  return request('/pedidos?estado=Pendiente');
}

export function getPedido(pedidoId) {
  return request(`/pedidos/${pedidoId}`);
}

export function cambiarEstadoPedido(pedidoId, estatus) {
  return request(`/pedidos/${pedidoId}/estado`, {
    method: 'PUT',
    body: { estatus },
  });
}
```

- [ ] **Step 2: Create `mobile/screens/CocinaDetalleScreen.js`**

```js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido, cambiarEstadoPedido } from '../api/pedidos_cocina';
import { ApiError } from '../api/client';

const SIGUIENTE_ESTATUS = {
  Pendiente: 'En preparación',
  'En preparación': 'Listo',
};

export default function CocinaDetalleScreen({ route, navigation }) {
  const { pedidoId } = route.params;
  const [pedido, setPedido] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cambiando, setCambiando] = useState(false);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPedido(await getPedido(pedidoId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar el pedido');
    } finally {
      setLoading(false);
    }
  }, [pedidoId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const avanzarEstado = async () => {
    const siguiente = SIGUIENTE_ESTATUS[pedido.estatus.nombre];
    if (!siguiente) return;

    setCambiando(true);
    setError('');
    try {
      const actualizado = await cambiarEstadoPedido(pedidoId, siguiente);
      setPedido(actualizado);
      if (actualizado.alertas_stock_bajo && actualizado.alertas_stock_bajo.length > 0) {
        setError(`Alerta de stock bajo: ${actualizado.alertas_stock_bajo.join(', ')}`);
      }
      if (siguiente === 'Listo') {
        navigation.goBack();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cambiar el estatus');
    } finally {
      setCambiando(false);
    }
  };

  if (loading || !pedido) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  const siguiente = SIGUIENTE_ESTATUS[pedido.estatus.nombre];

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>

      <Text style={styles.title}>Pedido #{pedido.id} — Mesa {pedido.id_mesa}</Text>
      <Text style={styles.estado}>Estado: {pedido.estatus.nombre}</Text>

      {pedido.detalle.map((item) => (
        <View key={item.id} style={styles.card}>
          <Text style={styles.producto}>{item.producto.nombre} x{item.cantidad}</Text>
          {item.especificaciones ? <Text style={{ color: 'gray' }}>{item.especificaciones}</Text> : null}
        </View>
      ))}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {siguiente ? (
        <TouchableOpacity style={styles.button} onPress={avanzarEstado} disabled={cambiando}>
          <Text style={styles.buttonText}>
            {cambiando ? 'Actualizando...' : `Marcar como ${siguiente}`}
          </Text>
        </TouchableOpacity>
      ) : (
        <Text style={{ color: 'gray', textAlign: 'center' }}>No hay más transiciones desde cocina</Text>
      )}

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  estado: { fontSize: 16, fontWeight: 'bold', color: '#E67E22', marginBottom: 15 },
  error: { color: '#C0392B', marginBottom: 15, textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 15, borderRadius: 12, marginBottom: 10, elevation: 3 },
  producto: { fontSize: 16, fontWeight: 'bold' },
  button: { backgroundColor: '#2E1B0F', padding: 14, borderRadius: 10, alignItems: 'center', marginTop: 10 },
  buttonText: { color: 'white', fontWeight: 'bold' },
});
```

- [ ] **Step 3: Replace `mobile/screens/ColaPedidosScreen.js` entirely**

```js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getColaPendientes } from '../api/pedidos_cocina';
import { ApiError } from '../api/client';

export default function ColaPedidosScreen({ navigation }) {
  const [pedidos, setPedidos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPedidos(await getColaPendientes());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Cola de Pedidos</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={pedidos}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.card}>

            <Text style={styles.mesa}>Mesa {item.id_mesa}</Text>
            <Text>Items: {item.detalle.length}</Text>
            <Text>Estado: {item.estatus.nombre}</Text>

            <TouchableOpacity
              style={styles.button}
              onPress={() => navigation.navigate('CocinaDetalle', { pedidoId: item.id })}
            >
              <Text style={{ color: 'white' }}>Ver preparación</Text>
            </TouchableOpacity>

          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 15, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  card: { backgroundColor: 'white', padding: 15, marginBottom: 12, borderRadius: 12 },
  mesa: { fontSize: 18, fontWeight: 'bold', marginBottom: 5 },
  button: { marginTop: 10, backgroundColor: '#2E1B0F', padding: 10, borderRadius: 8, alignItems: 'center' }
});
```

- [ ] **Step 4: Wire the live count in `mobile/screens/CocinaScreen.js`**

Replace lines 1-15 with:

```js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getColaPendientes } from '../api/pedidos_cocina';

export default function CocinaScreen({ navigation }) {
  const [pendientes, setPendientes] = useState(0);

  useFocusEffect(
    useCallback(() => {
      getColaPendientes()
        .then((data) => setPendientes(data.length))
        .catch(() => setPendientes(0));
    }, [])
  );

  return (
    <View style={styles.container}>

      <Text style={styles.title}> Cocina</Text>
      <Text style={styles.subtitle}>Gestión operativa de pedidos</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Estado del sistema</Text>
        <Text>Cocina activa</Text>
        <Text>Pedidos en espera: {pendientes}</Text>
      </View>
```

(the rest of the file — the three navigation buttons and `StyleSheet.create` — stays exactly as-is).

- [ ] **Step 5: Register `CocinaDetalle` in `mobile/App.js`**

Add `import CocinaDetalleScreen from './screens/CocinaDetalleScreen';` near the other screen imports, and add:

```jsx
        <Stack.Screen
          name="CocinaDetalle"
          component={CocinaDetalleScreen}
        />
```

- [ ] **Step 6: Manual verification — full Cocina flow**

1. As Mesero (or via curl with the Mesero token), create a fresh pedido so there's a real "Pendiente" row.
2. Log in as `cocinero@coffeecode.com`, Home → Cocina. Expected: "Pedidos en espera" shows the real count (≥1).
3. Tap "Cola de pedidos". Expected: the pedido from step 1 appears with correct mesa/item count.
4. Tap "Ver preparación", tap "Marcar como En preparación", confirm via `GET /pedidos/{id}` the estatus changed.
5. Tap "Marcar como Listo". Confirm atomic ingredient stock discount happened (`GET /ingredientes/{id}` before/after matches the recipe quantities), and the screen navigates back to the (now-empty, since it's no longer Pendiente) cola.

- [ ] **Step 7: Commit**

```bash
git add mobile/api/pedidos_cocina.js mobile/screens/CocinaDetalleScreen.js mobile/screens/ColaPedidosScreen.js mobile/screens/CocinaScreen.js mobile/App.js
git commit -m "feat(mobile): cola de pedidos real y cambio de estatus desde Cocina"
```

---

## Fase 2 complete when

All 3 tasks committed, Task 3 Step 6's full Cocina flow manual verification passes against the live Docker API, including the atomic stock discount on "Listo".
