# Mobile Fase 3 — Caja Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Caja flow (ver pedidos listos para cobrar → procesar pago → registrar gastos) end-to-end against the real FastAPI backend.

**Architecture:** Reuses `api/client.js`, `auth/session.js`, `auth/AuthContext.js` from Fase 0 (already merged — do not modify). Adds Caja-only API modules and rewrites the three Caja screens (currently pure mock `useState` arrays with a fake 2-second `setTimeout` "payment") to call the real endpoints.

**Tech Stack:** React Native (Expo), React Navigation 7, `fetch` via the shared `api/client.js`.

## Global Constraints

- Prerequisite: Fase 0 merged to `main` before this plan starts.
- **Isolation rule:** this plan creates `api/pedidos_caja.js` as its OWN file for pedido reads (`getPedidosListos`, `getPedido`) instead of modifying the shared `api/pedidos.js` from Fase 0 or Fase 2's `api/pedidos_cocina.js` — Fase 2 (Cocina) runs in a parallel worktree and also reads pedidos; two phases editing the same file would conflict on merge. Minor duplication of `request()` wrapper calls is the accepted tradeoff for merge safety.
- Real business flow (confirmed against `api/app/services/pedidos.py` and prior session verification): pedido reaches estatus **"Listo"** in Cocina, THEN Caja charges it via `POST /ventas`, THEN Mesero marks it **"Entregado"**. Caja's queue is `GET /pedidos?estado=Listo`, not "Pendiente".
- **Known API limitation, not a bug to fix here:** there is no `GET /gastos` list endpoint — only `POST /gastos`. `GastosScreen` therefore shows expenses added in the current app session (client-side accumulation, same pattern the mock already uses) plus the authoritative period total pulled from `GET /caja/resumen`. Do not invent a new backend endpoint for this plan.
- This plan touches ONLY: `api/caja.js` (new), `api/pedidos_caja.js` (new), `api/gastos.js` (new), `screens/CajaScreen.js`, `screens/PagoScreen.js`, `screens/GastosScreen.js`. It must NOT touch any Cocina screen/file, `api/pedidos.js`, or `api/pedidos_cocina.js`.
- No axios, no socket.io, no new test framework — manual verification against the live Docker API, per `docs/superpowers/specs/2026-08-03-mobile-backend-wiring-design.md`.
- Seed credentials: `cajero@coffeecode.com` / `Cajero123!`.
- Real métodos de pago (must match backend's `MetodoPagoNombre` exactly, from `api/app/core/constants.py:28-32`): `"Efectivo"`, `"Tarjeta débito"`, `"Tarjeta crédito"`, `"Transferencia"`.

---

### Task 1: Caja screen — real queue from `GET /pedidos?estado=Listo`

**Files:**
- Create: `mobile/api/pedidos_caja.js`
- Create: `mobile/api/caja.js`
- Modify: `mobile/screens/CajaScreen.js` (full replacement — mock 3-item hardcoded array replaced with real API call)

**Interfaces:**
- Consumes: `request` from `api/client.js`.
- Produces: `pedidos_caja.js` exports `getPedidosListos(): Promise<PedidoOut[]>`, `getPedido(id): Promise<PedidoOut>`. `caja.js` exports `registrarVenta({pedidoId, metodoPago, monto}): Promise<TicketOut>`, `getResumenCaja(desde?, hasta?): Promise<{desde,hasta,total_ventas,total_gastos,ganancia_neta}>`. Consumed by Task 2 (`PagoScreen`) and Task 3 (`GastosScreen`).

- [ ] **Step 1: Create `mobile/api/pedidos_caja.js`**

```js
import { request } from './client';

export function getPedidosListos() {
  return request('/pedidos?estado=Listo');
}

export function getPedido(pedidoId) {
  return request(`/pedidos/${pedidoId}`);
}
```

- [ ] **Step 2: Create `mobile/api/caja.js`**

```js
import { request } from './client';

export function registrarVenta({ pedidoId, metodoPago, monto }) {
  return request('/ventas', {
    method: 'POST',
    body: { pedido_id: pedidoId, metodo_pago: metodoPago, monto },
  });
}

export function getResumenCaja(desde, hasta) {
  const params = new URLSearchParams();
  if (desde) params.append('desde', desde);
  if (hasta) params.append('hasta', hasta);
  const query = params.toString();
  return request(`/caja/resumen${query ? `?${query}` : ''}`);
}
```

- [ ] **Step 3: Replace `mobile/screens/CajaScreen.js` entirely**

```js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedidosListos } from '../api/pedidos_caja';
import { ApiError } from '../api/client';

export default function CajaScreen({ navigation }) {
  const [pedidos, setPedidos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPedidos(await getPedidosListos());
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

      <Text style={styles.title}>Caja</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={pedidos}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingBottom: 30 }}
        ListEmptyComponent={<Text style={{ textAlign: 'center', color: 'gray' }}>Sin pedidos listos para cobrar</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.mesa}>Mesa {item.id_mesa}</Text>
            <Text>Pedido #{item.id} — {item.detalle.length} ítem(s)</Text>

            <TouchableOpacity
              style={styles.button}
              onPress={() => navigation.navigate('Pago', { pedidoId: item.id })}
            >
              <Text style={{ color: 'white' }}>Cobrar</Text>
            </TouchableOpacity>
          </View>
        )}
        ListFooterComponent={() => (
          <TouchableOpacity
            style={[styles.button, { marginTop: 15, backgroundColor: '#444' }]}
            onPress={() => navigation.navigate('Gastos')}
          >
            <Text style={{ color: 'white' }}>Gastos y cuentas</Text>
          </TouchableOpacity>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  card: { backgroundColor: '#fff', padding: 15, marginBottom: 10, borderRadius: 10 },
  mesa: { fontSize: 18, fontWeight: 'bold' },
  button: { marginTop: 10, backgroundColor: '#2E1B0F', padding: 10, borderRadius: 8, alignItems: 'center' }
});
```

- [ ] **Step 4: Manual verification**

Ensure a pedido has been marked "Listo" by Cocina (Fase 2's flow, or `PUT /pedidos/{id}/estado` via Postman). Log in as `cajero@coffeecode.com`, Home → Caja. Expected: that pedido appears with correct mesa/item count; tapping "Cobrar" navigates to `Pago` with the right `pedidoId`.

- [ ] **Step 5: Commit**

```bash
git add mobile/api/pedidos_caja.js mobile/api/caja.js mobile/screens/CajaScreen.js
git commit -m "feat(mobile): CajaScreen real, cola de pedidos Listo para cobrar"
```

---

### Task 2: Pago screen — real `POST /ventas`

**Files:**
- Modify: `mobile/screens/PagoScreen.js` (full replacement — fake `setTimeout` payment replaced with a real `registrarVenta` call; receives `pedidoId` instead of an inline mock `pedido` object)

**Interfaces:**
- Consumes: `getPedido(pedidoId)` from `api/pedidos_caja.js`, `registrarVenta` from `api/caja.js` (Task 1). `pedidoId` route param produced by Task 1's `CajaScreen`.

- [ ] **Step 1: Replace `mobile/screens/PagoScreen.js` entirely**

```js
import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido } from '../api/pedidos_caja';
import { registrarVenta } from '../api/caja';
import { ApiError } from '../api/client';

const METODOS = [
  { key: 'Efectivo', label: 'Efectivo' },
  { key: 'Tarjeta débito', label: 'Tarjeta débito' },
  { key: 'Tarjeta crédito', label: 'Tarjeta crédito' },
  { key: 'Transferencia', label: 'Transferencia' },
];

export default function PagoScreen({ route, navigation }) {
  const { pedidoId } = route.params;

  const [pedido, setPedido] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metodoPago, setMetodoPago] = useState('');
  const [monto, setMonto] = useState('');
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState(null);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      getPedido(pedidoId)
        .then(setPedido)
        .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudo cargar el pedido'))
        .finally(() => setLoading(false));
    }, [pedidoId])
  );

  const subtotalEstimado = pedido
    ? pedido.detalle.reduce((acc, item) => acc + Number(item.precio_unitario) * item.cantidad, 0)
    : 0;

  const pagar = async () => {
    if (!metodoPago) {
      setError('Selecciona un método de pago');
      return;
    }
    if (!monto || Number(monto) <= 0) {
      setError('Ingresa el monto recibido');
      return;
    }

    setProcesando(true);
    setError('');
    try {
      const ticket = await registrarVenta({ pedidoId, metodoPago, monto: Number(monto) });
      setResultado(ticket);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo procesar el pago');
    } finally {
      setProcesando(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  if (resultado) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>Pago registrado</Text>
        <Text style={styles.text}>Total: ${resultado.total}</Text>
        <Text style={styles.text}>Cambio: ${resultado.pago.cambio}</Text>
        <TouchableOpacity style={styles.payButton} onPress={() => navigation.navigate('Caja')}>
          <Text style={styles.payText}>Volver a Caja</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>

      <Text style={styles.title}>Procesar Pago</Text>

      <View style={styles.card}>
        <Text style={styles.subtitle}>Mesa {pedido.id_mesa} — Pedido #{pedido.id}</Text>

        {pedido.detalle.map((item) => (
          <Text key={item.id} style={styles.text}>
            {item.producto.nombre} x{item.cantidad} — ${item.precio_unitario}
          </Text>
        ))}

        <Text style={styles.total}>Subtotal (sin IVA): ${subtotalEstimado.toFixed(2)}</Text>
        <Text style={{ color: 'gray' }}>El total final con IVA lo calcula el servidor al confirmar.</Text>
      </View>

      <Text style={styles.subtitle}>Método de pago</Text>

      <View style={styles.row}>
        {METODOS.map((m) => (
          <TouchableOpacity
            key={m.key}
            style={[styles.button, metodoPago === m.key && styles.buttonActive]}
            onPress={() => setMetodoPago(m.key)}
            disabled={procesando}
          >
            <Text style={styles.buttonText}>{m.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.card}>
        <Text>Monto recibido</Text>
        <TextInput
          style={styles.input}
          keyboardType="numeric"
          placeholder="Ej. 200"
          value={monto}
          onChangeText={setMonto}
          editable={!procesando}
        />
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity style={styles.payButton} onPress={pagar} disabled={procesando}>
        {procesando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.payText}>Confirmar y Pagar</Text>
        )}
      </TouchableOpacity>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5', padding: 15 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 15 },
  subtitle: { fontSize: 18, fontWeight: 'bold', marginTop: 10 },
  card: { backgroundColor: 'white', padding: 15, borderRadius: 10, marginBottom: 15 },
  text: { fontSize: 16 },
  total: { fontSize: 18, fontWeight: 'bold', marginTop: 10 },
  error: { color: '#C0392B', marginBottom: 10, textAlign: 'center' },
  row: { flexDirection: 'row', flexWrap: 'wrap', marginVertical: 10 },
  button: { backgroundColor: '#ccc', padding: 10, borderRadius: 8, width: '48%', alignItems: 'center', marginBottom: 8, marginRight: '2%' },
  buttonActive: { backgroundColor: '#2E1B0F' },
  buttonText: { color: 'white' },
  input: { borderWidth: 1, borderColor: '#ccc', marginTop: 10, padding: 10, borderRadius: 8 },
  payButton: { backgroundColor: '#2E1B0F', padding: 15, borderRadius: 10, marginTop: 10, alignItems: 'center' },
  payText: { color: 'white', fontWeight: 'bold' }
});
```

- [ ] **Step 2: Update the navigation call site**

This screen now expects `route.params.pedidoId` (not a `pedido` object) — already satisfied by Task 1's `CajaScreen` rewrite (`navigation.navigate('Pago', { pedidoId: item.id })`). No further change needed here; this step just confirms the contract matches (no code to write, verification only).

- [ ] **Step 3: Manual verification**

From Task 1's verified Caja queue, tap "Cobrar" on a real pedido. Expected: real items + prices shown. Enter a `monto` below the true IVA-inclusive total, select "Efectivo": expected inline error "El monto recibido (...) es insuficiente...". Enter enough, confirm: expected success screen with real `total`/`cambio` from the API response. Confirm via `GET /pedidos/{id}` that `total` is now set (was `null` before payment).

- [ ] **Step 4: Commit**

```bash
git add mobile/screens/PagoScreen.js
git commit -m "feat(mobile): PagoScreen procesa pagos reales via POST /ventas"
```

---

### Task 3: Gastos screen — real `POST /gastos` + resumen de caja

**Files:**
- Create: `mobile/api/gastos.js`
- Modify: `mobile/screens/GastosScreen.js` (full replacement — mock local-only list gets a real `POST /gastos` call plus the authoritative period total from `GET /caja/resumen`; per-session list display is kept since there's no list endpoint, see Global Constraints)

**Interfaces:**
- Consumes: `getResumenCaja` from `api/caja.js` (Task 1).
- Produces: `crearGasto({concepto, monto}): Promise<GastoOut>`.

- [ ] **Step 1: Create `mobile/api/gastos.js`**

```js
import { request } from './client';

export function crearGasto({ concepto, monto }) {
  return request('/gastos', {
    method: 'POST',
    body: { concepto, monto },
  });
}
```

- [ ] **Step 2: Replace `mobile/screens/GastosScreen.js` entirely**

```js
import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { crearGasto } from '../api/gastos';
import { getResumenCaja } from '../api/caja';
import { ApiError } from '../api/client';

export default function GastosScreen() {

  const [descripcion, setDescripcion] = useState('');
  const [monto, setMonto] = useState('');
  const [gastosSesion, setGastosSesion] = useState([]);
  const [totalPeriodo, setTotalPeriodo] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  const cargarResumen = useCallback(async () => {
    try {
      const hoy = new Date();
      const desde = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()).toISOString();
      const resumen = await getResumenCaja(desde);
      setTotalPeriodo(resumen.total_gastos);
    } catch (err) {
      // el resumen es informativo; si falla no bloquea el registro de gastos
      setTotalPeriodo(null);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargarResumen();
    }, [cargarResumen])
  );

  const agregarGasto = async () => {
    if (!descripcion.trim() || !monto) {
      setError('Completa todos los campos');
      return;
    }

    setGuardando(true);
    setError('');
    try {
      const creado = await crearGasto({ concepto: descripcion.trim(), monto: parseFloat(monto) });
      setGastosSesion([creado, ...gastosSesion]);
      setDescripcion('');
      setMonto('');
      await cargarResumen();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el gasto');
    } finally {
      setGuardando(false);
    }
  };

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Caja - Gastos y Cuentas</Text>

      <View style={styles.card}>

        <TextInput
          placeholder="Descripción del gasto (mín. 3 caracteres)"
          value={descripcion}
          onChangeText={setDescripcion}
          style={styles.input}
        />

        <TextInput
          placeholder="Monto"
          value={monto}
          onChangeText={setMonto}
          keyboardType="numeric"
          style={styles.input}
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TouchableOpacity style={styles.btnAgregar} onPress={agregarGasto} disabled={guardando}>
          <Text style={styles.btnText}>{guardando ? 'Guardando...' : 'Agregar gasto'}</Text>
        </TouchableOpacity>

      </View>

      <View style={styles.totalBox}>
        <Text style={styles.totalText}>
          Total gastos de hoy (servidor): {totalPeriodo !== null ? `$${totalPeriodo}` : 'no disponible'}
        </Text>
      </View>

      <FlatList
        data={gastosSesion}
        keyExtractor={(item) => item.id.toString()}
        ListHeaderComponent={gastosSesion.length > 0 ? <Text style={{ marginBottom: 5, color: 'gray' }}>Registrados en esta sesión:</Text> : null}
        renderItem={({ item }) => (
          <View style={styles.item}>
            <View>
              <Text style={styles.desc}>{item.concepto}</Text>
              <Text style={styles.monto}>${item.monto}</Text>
            </View>
          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({

  container: { flex: 1, backgroundColor: '#F5F5F5', padding: 15 },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  card: { backgroundColor: 'white', padding: 15, borderRadius: 10, marginBottom: 10 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 10, marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  btnAgregar: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8 },
  btnText: { color: 'white', textAlign: 'center', fontWeight: 'bold' },
  totalBox: { backgroundColor: '#fff', padding: 15, borderRadius: 10, marginBottom: 10 },
  totalText: { fontSize: 16, fontWeight: 'bold' },
  item: { backgroundColor: 'white', padding: 15, borderRadius: 10, marginBottom: 10 },
  desc: { fontSize: 16, fontWeight: 'bold' },
  monto: { color: 'gray' },
});
```

- [ ] **Step 3: Manual verification**

Log in as `cajero@coffeecode.com`, Home → Caja → "Gastos y cuentas". Add a gasto with a description under 3 characters: expected inline error (backend `GastoCreate.concepto` has `min_length=3`, surfaced via `ApiError.message`). Add a valid one: expected it appears in the session list AND "Total gastos de hoy" updates to reflect it (confirm the number matches `GET /caja/resumen?desde=<today-midnight-ISO>` called directly).

- [ ] **Step 4: Commit**

```bash
git add mobile/api/gastos.js mobile/screens/GastosScreen.js
git commit -m "feat(mobile): GastosScreen registra gastos reales y muestra total de caja"
```

---

## Fase 3 complete when

All 3 tasks committed, each task's manual verification step passes against the live Docker API, including the full Listo → Cobrar → Pago-exitoso chain in Task 2.
