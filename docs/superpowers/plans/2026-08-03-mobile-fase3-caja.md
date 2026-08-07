# Mobile Fase 3 — Caja Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Caja flow (ver pedidos listos para cobrar → procesar pago → registrar gastos) end-to-end against the real FastAPI backend.

**Architecture:** Reuses `api/client.js`, `auth/session.js`, `auth/AuthContext.js` from Fase 0 (already merged — do not modify). Adds Caja-only API modules and rewrites the three Caja screens (currently pure mock `useState` arrays with a fake 2-second `setTimeout` "payment") to call the real endpoints.

**Tech Stack:** React Native (Expo), React Navigation 7, `fetch` via the shared `api/client.js`.

## Global Constraints

- Prerequisite: Fase 0 merged to `main` before this plan starts.
- **Isolation rule:** this plan creates `api/pedidos_caja.js` as its OWN file for pedido reads (`getPedidosListos`, `getPedido`) instead of modifying the shared `api/pedidos.js` from Fase 0 or Fase 2's `api/pedidos_cocina.js` — Fase 2 (Cocina) runs in a parallel worktree and also reads pedidos; two phases editing the same file would conflict on merge. Minor duplication of `request()` wrapper calls is the accepted tradeoff for merge safety.
- **Única excepción al aislamiento: `App.js`.** Los dos planes lo modifican para
  registrar una ruta nueva (Fase 2 añade `CocinaDetalle`, Fase 3 añade
  `Compras`), así que al fusionar worktrees paralelos es esperable un conflicto
  trivial en ese archivo — se resuelve conservando ambos `<Stack.Screen>` y
  ambos imports. No indica acoplamiento real: ningún otro archivo se comparte.
- Real business flow (confirmed against `api/app/services/pedidos.py` and prior session verification): pedido reaches estatus **"Listo"** in Cocina, THEN Caja charges it via `POST /ventas`, THEN Mesero marks it **"Entregado"**. Caja's queue is `GET /pedidos?estado=Listo`, not "Pendiente".
- **Known API limitation, not a bug to fix here:** there is no `GET /gastos` list endpoint — only `POST /gastos`. `GastosScreen` therefore shows expenses added in the current app session (client-side accumulation, same pattern the mock already uses) plus the authoritative period total pulled from `GET /caja/resumen`. Do not invent a new backend endpoint for this plan.
- This plan touches ONLY: `api/caja.js` (new), `api/pedidos_caja.js` (new), `api/gastos.js` (new), `api/ingredientes_caja.js` (new), `screens/CajaScreen.js`, `screens/PagoScreen.js`, `screens/GastosScreen.js`, `screens/ComprasScreen.js` (new), `App.js` (adds one route). It must NOT touch any Cocina screen/file, `api/pedidos.js`, `api/pedidos_cocina.js`, or `api/ingredientes.js` (Fase 2's). `api/mesas.js` (Fase 0) se **importa sin modificar**.
- **Un pedido pagado NO cambia de estatus.** `registrar_venta`
  (`api/app/services/ventas.py:63`) solo hace `pedido.total = total`; el
  `id_estatus` sigue en `Listo` hasta que el Mesero marque `Entregado`
  (Fase 0, `DetalleScreen`). Por eso la cola de Caja **debe** distinguir los
  ya cobrados: si no, siguen ofreciendo "Cobrar" y el reintento devuelve 409
  "El pedido ya tiene un pago registrado"
  (`api/app/services/ventas.py:26-31`) — exactamente lo que afirma
  `fuego-rol-cajero` en "[ERROR] Pago duplicado". El discriminador es
  `pedido.total !== null`.
- **Techo conocido, no se arregla aquí:** `GET /pedidos` usa `limit=50`
  (`api/app/routers/pedidos.py:42`). Combinado con lo anterior, un día ocupado
  puede truncar la cola de Caja. Paginación fuera de alcance; se documenta.
- **Orden de verificación (no de código):** los Steps de verificación manual
  de los Tasks 1 y 2 necesitan un pedido real en estatus `Listo`, que produce
  Fase 2 (Cocina). Los archivos de ambos planes son disjuntos (salvo `App.js`,
  ver arriba) y pueden
  implementarse en paralelo; solo la **verificación** requiere que exista un
  `Listo`. Fallback ya previsto: generarlo por Postman con
  `PUT /pedidos/{id}/estado` usando un token de Cocinero.
- **`PedidoOut` no expone `numero_mesa`**, solo `id_mesa` (PK)
  (`api/app/models/pedidos.py:55-65`). Caja ve pedidos de mesas distintas y no
  recibe parámetros de navegación desde Mesas, así que hace un `GET /mesas`
  y une client-side por `id_mesa`.
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
import { getMesas } from '../api/mesas';
import { ApiError } from '../api/client';

export default function CajaScreen({ navigation }) {
  const [pedidos, setPedidos] = useState([]);
  const [numeroPorMesa, setNumeroPorMesa] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      // PedidoOut solo trae id_mesa (PK); el número visible vive en MesaOut.
      const [lista, mesas] = await Promise.all([getPedidosListos(), getMesas()]);
      setPedidos(lista);
      setNumeroPorMesa(Object.fromEntries(mesas.map((m) => [m.id, m.numero_mesa])));
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
        renderItem={({ item }) => {
          // registrar_venta pone `total` pero deja el estatus en `Listo`
          // (api/app/services/ventas.py:63): el pedido sigue en esta cola
          // hasta que el Mesero lo marque Entregado. Ofrecerle "Cobrar" otra
          // vez garantiza un 409 de pago duplicado.
          const pagado = item.total !== null;
          return (
            <View style={[styles.card, pagado && styles.cardPagado]}>
              <Text style={styles.mesa}>Mesa {numeroPorMesa[item.id_mesa] ?? item.id_mesa}</Text>
              <Text>Pedido #{item.id} — {item.detalle.length} ítem(s)</Text>

              {pagado ? (
                <Text style={styles.pagado}>
                  Cobrado (${item.total}) — pendiente de entrega por el mesero
                </Text>
              ) : (
                <TouchableOpacity
                  style={styles.button}
                  onPress={() =>
                    navigation.navigate('Pago', {
                      pedidoId: item.id,
                      numeroMesa: numeroPorMesa[item.id_mesa],
                    })
                  }
                >
                  <Text style={{ color: 'white' }}>Cobrar</Text>
                </TouchableOpacity>
              )}
            </View>
          );
        }}
        ListFooterComponent={() => (
          <View>
            <TouchableOpacity
              style={[styles.button, { marginTop: 15, backgroundColor: '#444' }]}
              onPress={() => navigation.navigate('Gastos')}
            >
              <Text style={{ color: 'white' }}>Gastos y cuentas</Text>
            </TouchableOpacity>
            {/* Task 4 agrega aquí el botón "Registrar compra de insumo",
                junto con la ruta `Compras` que necesita para no crashear. */}
          </View>
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
  cardPagado: { opacity: 0.6 },
  pagado: { marginTop: 8, color: '#1F618D', fontWeight: 'bold' },
  mesa: { fontSize: 18, fontWeight: 'bold' },
  button: { marginTop: 10, backgroundColor: '#2E1B0F', padding: 10, borderRadius: 8, alignItems: 'center' }
});
```

El acceso a compras de insumo **no** se agrega aquí: su botón vive en Task 4,
junto con la ruta `Compras` que necesita. Añadirlo antes sería un enlace a una
ruta inexistente (crash de React Navigation).

- [ ] **Step 4: Manual verification**

Ensure a pedido has been marked "Listo" by Cocina (Fase 2's flow, or `PUT /pedidos/{id}/estado` via Postman). Log in as `cajero@coffeecode.com`, Home → Caja. Expected: that pedido appears with correct mesa/item count; tapping "Cobrar" navigates to `Pago` with the right `pedidoId`.

Then verify the paid-order distinction: after completing Task 2's payment on
a pedido, come back to Caja. Expected: ese pedido **sigue** en la lista (su
estatus sigue siendo `Listo`) pero atenuado, con "Cobrado ($X) — pendiente de
entrega por el mesero" y **sin** botón "Cobrar". Confirm via
`GET /pedidos/{id}` que `total` ya no es `null` y `estatus.nombre` sigue
siendo `"Listo"`. Cuando el Mesero lo marque `Entregado` (Fase 0), desaparece
de esta cola.

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
  const { pedidoId, numeroMesa } = route.params;

  const [pedido, setPedido] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metodoPago, setMetodoPago] = useState('');
  const [monto, setMonto] = useState('');
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState(null);

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

  if (loading && !pedido) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  // Sin este guard, si el GET falla el render de abajo lee pedido.id_mesa /
  // pedido.detalle sobre null y revienta con TypeError. Mismo patrón que
  // DetalleScreen (Fase 0, Task 7).
  if (error && !pedido) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error}</Text>
        <TouchableOpacity style={styles.payButton} onPress={cargar}>
          <Text style={styles.payText}>Reintentar</Text>
        </TouchableOpacity>
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
        <Text style={styles.subtitle}>Mesa {numeroMesa ?? pedido.id_mesa} — Pedido #{pedido.id}</Text>

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

Then confirm the duplicate-payment guard end-to-end: without marking the
pedido `Entregado`, go back to Caja. Expected: the paid pedido shows as
"Cobrado" with no "Cobrar" button, so the 409 is unreachable from the UI. If
you force it via Postman (`POST /ventas` again on the same `pedido_id`),
expected `409 "El pedido ya tiene un pago registrado"` — the same assertion as
`fuego-rol-cajero` "[ERROR] Pago duplicado".

Finalmente, el caso de carga fallida: apaga la API y navega a `Pago`. Expected:
mensaje de error con botón "Reintentar" — **no** una pantalla en blanco ni un
crash por leer `pedido.detalle` sobre `null`.

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
      // updater funcional: evita perder un gasto si dos altas caen seguidas
      // sobre el mismo `gastosSesion` capturado en el closure.
      setGastosSesion((actual) => [creado, ...actual]);
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

### Task 4: Registrar compra de insumo — `POST /compras` (solo Administrador)

> **Alcance restringido a propósito — leer antes de implementar.**
> `POST /compras` acepta `Cajero|Administrador`
> (`api/app/routers/caja.py:26,53`), pero el selector de ingrediente necesita
> `GET /ingredientes`, que es `Cocinero|Administrador`
> (`api/app/routers/ingredientes.py:20`). **Un Cajero recibe 403 al listar
> ingredientes**, y `fuego-rol-cajero` afirma ese 403 como comportamiento
> correcto ("[ERROR] Cajero intenta listar ingredientes"). `web-admin` nunca
> topó con esto porque rechaza todo login que no sea Administrador
> (`web-admin/app/blueprints/auth.py:23-25`); la propia suite
> `fuego-flujo-compra-insumos` incluye un request llamado "Login Admin (solo
> para leer inventario)" para sortearlo. Mobile no puede cambiar de token a
> media pantalla.
>
> **Resolución de este plan:** la pantalla se entrega funcionando **solo para
> `Administrador`** (rol ya alcanzable: `HomeScreen` de Fase 0 le muestra
> Mesero/Cocina/Caja). El punto de entrada en `CajaScreen` está condicionado a
> `rol === 'Administrador'` y se agrega en el **Step 4 de este mismo Task**,
> no en Task 1: el botón y la ruta `Compras` tienen que aterrizar en el mismo
> commit, o entre Task 1 y Task 4 un Administrador que lo toque navega a una
> ruta inexistente. **No se implementa ningún cambio de
> backend.** Si se quiere que un Cajero registre compras desde el móvil, hace
> falta una decisión del usuario sobre un cambio de API (abrir
> `GET /ingredientes` a Cajero, o un `GET /ingredientes/nombres` de
> solo-lectura) — registrado como decisión abierta en la spec.

**Files:**
- Create: `mobile/api/ingredientes_caja.js`
- Create: `mobile/screens/ComprasScreen.js`
- Modify: `mobile/api/caja.js` (adds `registrarCompra` — additive)
- Modify: `mobile/App.js` (adds the `Compras` route)
- Modify: `mobile/screens/CajaScreen.js` (adds the Administrador-only entry point — additive, Step 4)

**Interfaces:**
- Consumes: `request` from `api/client.js`, `useAuth()` for `rol` (both in `ComprasScreen` and in `CajaScreen`'s entry-point gate).
- Produces: `getIngredientes(): Promise<IngredienteOut[]>`, `registrarCompra({ingredienteId, cantidad, monto}): Promise<{gasto, ingrediente_id, nuevo_stock}>` (shape from `CompraOut`, `api/app/models/ventas.py:59-62`).

- [ ] **Step 1: Create `mobile/api/ingredientes_caja.js`**

```js
import { request } from './client';

// Archivo propio por la regla de aislamiento: api/ingredientes.js pertenece a
// Fase 2 (Cocina) y puede estar en un worktree paralelo.
// OJO: GET /ingredientes es Cocinero|Administrador. Con token de Cajero
// devuelve 403 — por eso ComprasScreen es solo para Administrador.
export function getIngredientes() {
  return request('/ingredientes');
}
```

- [ ] **Step 2: Append `registrarCompra` to `mobile/api/caja.js`**

```js
export function registrarCompra({ ingredienteId, cantidad, monto }) {
  return request('/compras', {
    method: 'POST',
    body: { ingrediente_id: ingredienteId, cantidad, monto },
  });
}
```

`CompraCreate` (`api/app/models/ventas.py:53-56`) exige `cantidad` y `monto`
con `Field(gt=0)`: cero o negativo devuelve **422 con `detail` como array**,
que el `client.js` corregido en Fase 0 ya sabe aplanar. Es exactamente lo que
afirman "[ERROR] Cantidad negativa" / "[ERROR] Monto en cero" de
`fuego-flujo-compra-insumos`.

- [ ] **Step 3: Create `mobile/screens/ComprasScreen.js`**

```js
import React, { useCallback, useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getIngredientes } from '../api/ingredientes_caja';
import { registrarCompra } from '../api/caja';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export default function ComprasScreen() {
  const { rol } = useAuth();
  const [ingredientes, setIngredientes] = useState([]);
  const [seleccionado, setSeleccionado] = useState(null);
  const [cantidad, setCantidad] = useState('');
  const [monto, setMonto] = useState('');
  const [loading, setLoading] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setIngredientes(await getIngredientes());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar el inventario');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const comprar = async () => {
    if (!seleccionado) {
      setError('Selecciona un ingrediente');
      return;
    }
    setGuardando(true);
    setError('');
    setAviso('');
    try {
      const resultado = await registrarCompra({
        ingredienteId: seleccionado.id,
        cantidad: Number(cantidad),
        monto: Number(monto),
      });
      setAviso(`Compra registrada. Nuevo stock de ${seleccionado.nombre}: ${resultado.nuevo_stock} ${seleccionado.unidad}.`);
      setCantidad('');
      setMonto('');
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar la compra');
    } finally {
      setGuardando(false);
    }
  };

  if (rol !== 'Administrador') {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>
          Registrar compras requiere el rol Administrador: el listado de
          ingredientes no está disponible para Cajero.
        </Text>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Registrar compra de insumo</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {aviso ? <Text style={styles.aviso}>{aviso}</Text> : null}

      <TextInput placeholder="Cantidad a ingresar" value={cantidad} onChangeText={setCantidad} keyboardType="numeric" style={styles.input} />
      <TextInput placeholder="Monto total de la compra" value={monto} onChangeText={setMonto} keyboardType="numeric" style={styles.input} />

      <TouchableOpacity style={styles.btn} onPress={comprar} disabled={guardando}>
        <Text style={styles.btnText}>
          {guardando ? 'Registrando...' : seleccionado ? `Comprar ${seleccionado.nombre}` : 'Selecciona un ingrediente'}
        </Text>
      </TouchableOpacity>

      <FlatList
        data={ingredientes}
        keyExtractor={(i) => i.id.toString()}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.card, seleccionado && seleccionado.id === item.id && styles.cardSel]}
            onPress={() => setSeleccionado(item)}
          >
            <Text style={styles.name}>{item.nombre}</Text>
            <Text>Stock: {item.stock_actual} {item.unidad}</Text>
          </TouchableOpacity>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 15, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10, textAlign: 'center' },
  aviso: { color: '#1F618D', marginBottom: 10 },
  input: { backgroundColor: 'white', padding: 10, marginBottom: 8, borderRadius: 8 },
  btn: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8, marginBottom: 10 },
  btnText: { color: 'white', textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 10, marginBottom: 8, borderRadius: 8, borderWidth: 2, borderColor: 'transparent' },
  cardSel: { borderColor: '#2E1B0F' },
  name: { fontSize: 16, fontWeight: 'bold' },
});
```

- [ ] **Step 4: Register the route in `mobile/App.js` and add the entry point in `CajaScreen`**

Add `import ComprasScreen from './screens/ComprasScreen';` near the other
screen imports, and:

```jsx
        <Stack.Screen
          name="Compras"
          component={ComprasScreen}
        />
```

En el **mismo commit**, agregar el punto de entrada en
`mobile/screens/CajaScreen.js` (Task 1 lo dejó fuera a propósito). Añadir el
import y el hook:

```js
import { useAuth } from '../auth/AuthContext';
```

```js
  const { rol } = useAuth();
```

y, dentro del `ListFooterComponent`, debajo del botón "Gastos y cuentas"
(donde Task 1 dejó el comentario que apunta a este Step):

```jsx
            {rol === 'Administrador' && (
              <TouchableOpacity
                style={[styles.button, { marginTop: 10, backgroundColor: '#444' }]}
                onPress={() => navigation.navigate('Compras')}
              >
                <Text style={{ color: 'white' }}>Registrar compra de insumo</Text>
              </TouchableOpacity>
            )}
```

- [ ] **Step 5: Manual verification**

1. Log in as `cajero@coffeecode.com`, Home → Caja. Expected: **no** aparece el
   botón "Registrar compra de insumo" (rol distinto de Administrador).
2. Log in as the seed Administrador, Home → Caja. Expected: el botón
   "Registrar compra de insumo" **sí** aparece; al tocarlo abre `Compras` (la
   ruta ya existe, agregada en el Step 4) con la lista real de ingredientes.
3. Selecciona uno, cantidad `-5`: expected inline error legible del 422 (no
   `[object Object]` — esto valida la corrección de `client.js` de Fase 0).
4. Monto `0`: expected otro 422 legible.
5. Cantidad y monto positivos: expected "Compra registrada. Nuevo stock de
   X: N." Confirm via `GET /ingredientes/{id}` que el stock subió exactamente
   `cantidad`, y via `GET /caja/resumen` que `total_gastos` subió exactamente
   `monto` (`POST /compras` hace ambas cosas en una transacción,
   `api/app/services/gastos.py::registrar_compra`).

- [ ] **Step 6: Commit**

```bash
git add mobile/api/ingredientes_caja.js mobile/api/caja.js mobile/screens/ComprasScreen.js mobile/screens/CajaScreen.js mobile/App.js
git commit -m "feat(mobile): registrar compra de insumo (solo Administrador)"
```

---

## Fase 3 complete when

All 4 tasks committed, each task's manual verification step passes against the
live Docker API, including the full Listo → Cobrar → Pago-exitoso chain in
Task 2, the paid-order distinction in Task 1 Step 4, and the Administrador-only
compras flow in Task 4.
