# Mobile Fase 0 — Infra compartida + Mesero end-to-end Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Mesero flow (login → ver mesas → crear pedido → ver detalle) end-to-end against the real FastAPI backend, and build the shared HTTP/auth infrastructure that Fase 2 (Cocina) and Fase 3 (Caja) will reuse without modification.

**Architecture:** A single `fetch`-based `api/client.js` handles all HTTP calls (base URL, JSON, auth header, error normalization). `expo-secure-store` persists the JWT; `auth/AuthContext.js` exposes `{token, rol, userId, login, logout}` to the whole app via React Context. Screens call thin per-resource modules (`api/auth.js`, `api/mesas.js`, `api/productos.js`, `api/pedidos.js`) — never `fetch` directly.

**Tech Stack:** React Native (Expo SDK 54), React Navigation 7 (native-stack), `expo-secure-store` (new dependency), plain `fetch`.

## Global Constraints

- No axios, no socket.io, no new test framework — per spec `docs/superpowers/specs/2026-08-03-mobile-backend-wiring-design.md`, verification is manual against the live Docker API.
- API base URL must be LAN-IP-configurable (Expo Go on a physical phone cannot reach `localhost`) via `app.config.js` → `extra.apiUrl`.
- This plan runs FIRST and sequentially, directly on `main` (or its own short-lived branch) — Fase 2/3 plans assume `api/client.js`, `auth/session.js`, `auth/AuthContext.js` already exist and are stable.
- Seed credentials for manual verification (from `api/app/seed.py`): `mesero@coffeecode.com` / `Mesero123!`.
- Every screen file this plan touches is listed explicitly in each task's **Files** block — no silent edits.

---

### Task 1: API base URL config

**Files:**
- Create: `mobile/app.config.js`
- Create: `mobile/config.js`
- Modify: `mobile/package.json` (no dependency change, just confirms `expo` version supports `app.config.js` — SDK 54 does, no action needed beyond verifying it loads)

**Interfaces:**
- Produces: `config.js` exports `API_URL: string` — every later task's API module imports this indirectly via `api/client.js`.

- [ ] **Step 1: Create `mobile/app.config.js`**

```js
export default {
  expo: {
    name: 'coffeecodemovil',
    slug: 'coffeecodemovil',
    version: '1.0.0',
    orientation: 'portrait',
    extra: {
      apiUrl: process.env.API_URL || 'http://192.168.1.100:8000',
    },
  },
};
```

Replace `192.168.1.100` with the actual LAN IP of the machine running `docker compose` for the API (find it with `ipconfig` on Windows, look for the IPv4 address of the active network adapter).

> **Nota (limitación conocida, fuera de alcance):** `mobile/` no tiene ni
> tuvo nunca un `app.json`. Este `app.config.js` lleva lo mínimo para correr
> en Expo Go. Si en el futuro se hace `expo prebuild` o un build de EAS habrá
> que reponer `icon`, `splash` y `assetBundlePatterns`. No se agregan aquí:
> no aportan nada al wiring y solo añaden superficie que mantener.

- [ ] **Step 2: Create `mobile/config.js`**

```js
import Constants from 'expo-constants';

export const API_URL = Constants.expoConfig.extra.apiUrl;
```

- [ ] **Step 3: Verify `expo-constants` is available**

Run: `cd mobile && npx expo install expo-constants`

This is a peer dependency of Expo SDK 54 and is likely already present transitively, but `expo install` ensures the correct pinned version is in `package.json`.

- [ ] **Step 4: Verify the app still boots**

Run: `cd mobile && npx expo start` — scan the QR with Expo Go, confirm the Splash → Login screen still renders (no config-loading crash). Stop the dev server after confirming (Ctrl+C).

- [ ] **Step 5: Commit**

```bash
git add mobile/app.config.js mobile/config.js mobile/package.json mobile/package-lock.json
git commit -m "feat(mobile): configurar API_URL vía app.config.js"
```

---

### Task 2: HTTP client + token storage

**Files:**
- Create: `mobile/auth/session.js`
- Create: `mobile/api/client.js`
- Modify: `mobile/package.json` (add `expo-secure-store`)

**Interfaces:**
- Consumes: `API_URL` from `mobile/config.js` (Task 1).
- Produces: `session.js` exports `saveToken(token): Promise<void>`, `getToken(): Promise<string|null>`, `clearToken(): Promise<void>`, `decodeToken(token): {rol, user_id, exp}`. `client.js` exports `request(path, {method, body, auth}): Promise<any>` and `class ApiError extends Error { status, message }`. Both are consumed by every `api/*.js` module in this and later phases.

- [ ] **Step 1: Install expo-secure-store**

Run: `cd mobile && npx expo install expo-secure-store`

- [ ] **Step 2: Create `mobile/auth/session.js`**

```js
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'coffeecode_token';

export async function saveToken(token) {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function getToken() {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function clearToken() {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

export function decodeToken(token) {
  try {
    const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    // atob de Hermes exige padding múltiplo de 4; base64url lo omite.
    const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4);
    return JSON.parse(atob(padded));
  } catch {
    return {};
  }
}
```

Hermes (el motor JS de React Native en Expo SDK 54) ya expone `atob` global —
no hace falta el decodificador base64 a mano ni una dependencia. El único
detalle real es el padding, que base64url omite y `atob` exige.

- [ ] **Step 3: Create `mobile/api/client.js`**

```js
import { API_URL } from '../config';
import { getToken, clearToken } from '../auth/session';

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// AuthContext registra aquí su forceLogout. client.js no importa React ni
// React Navigation: solo guarda un callback opcional.
let onUnauthorized = null;

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

function mensajeDeError(data, status) {
  const detail = data && data.detail;
  // FastAPI 422: detail es [{msg, loc, type}, ...], no un string.
  if (Array.isArray(detail)) {
    const msgs = detail.map((e) => e && e.msg).filter(Boolean);
    return msgs.length ? msgs.join('; ') : `Error ${status}`;
  }
  if (typeof detail === 'string' && detail) return detail;
  return `Error ${status}`;
}

export async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };

  if (auth) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (networkError) {
    throw new ApiError(0, 'Sin conexión con el servidor');
  }

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null; // respuesta no-JSON (proxy/502): cae al mensaje genérico
  }

  if (!response.ok) {
    if (response.status === 401 && auth) {
      await clearToken();
      if (onUnauthorized) onUnauthorized();
    }
    throw new ApiError(response.status, mensajeDeError(data, response.status));
  }

  return data;
}
```

Dos cosas que el borrador anterior rompía:

1. **422 de FastAPI.** `detail` llega como *array* de `{msg, loc, type}`, no
   como string. `(data && data.detail) || ...` lo pasaba tal cual a
   `super(message)` y la pantalla mostraba `[object Object]`. Esto lo ejercen
   directamente las suites fuego (422 en pedido vacío, cantidad negativa en
   compra, concepto de gasto corto).
2. **401.** Limpiar el token sin avisar a nadie dejaba a `AuthContext` con
   sesión fantasma: el usuario seguía en pantallas autenticadas viendo
   "Token inválido" en cada request. `setUnauthorizedHandler` desacopla el
   aviso; quien navega es `AuthContext` (Task 3). Es la misma semántica que
   el handler global de `web-admin` (`web-admin/app/__init__.py:46-52`).

- [ ] **Step 4: Manual verification against the live API**

With the Docker stack up (`docker compose up -d` in `api/`), run from a terminal reachable on the same network as the phone:

```bash
curl -X POST http://<LAN_IP>:8000/auth/login -H "Content-Type: application/json" -d "{\"correo_electronico\":\"mesero@coffeecode.com\",\"password\":\"Mesero123!\"}"
```

Expected: `200` with `{"access_token": "...", "rol": "Mesero"}`. This confirms the LAN IP in `app.config.js` (Task 1) is correct before wiring any screen to it.

- [ ] **Step 5: Commit**

```bash
git add mobile/auth/session.js mobile/api/client.js mobile/package.json mobile/package-lock.json
git commit -m "feat(mobile): cliente HTTP y almacenamiento seguro de token"
```

---

### Task 3: Auth context + real login screen

**Files:**
- Create: `mobile/api/auth.js`
- Create: `mobile/auth/AuthContext.js`
- Create: `mobile/navigationRef.js`
- Modify: `mobile/screens/LoginScreen.js` (replace the entire mock `login()` function and error handling — full rewrite, same visual layout/styles kept)
- Modify: `mobile/screens/SplashScreen.js` (replace the fixed 2s `setTimeout` → Login with a wait on `AuthContext.loading`)
- Modify: `mobile/App.js:22-24` (wrap `NavigationContainer` in `AuthProvider`, attach `navigationRef`)

**Interfaces:**
- Consumes: `request`/`ApiError` from `api/client.js`, `saveToken`/`decodeToken` from `auth/session.js` (Task 2).
- Produces: `AuthContext.js` exports `AuthProvider` (component) and `useAuth()` hook returning `{token, rol, userId, loading, login(correo, password): Promise<string>, logout(): Promise<void>}`. Consumed by `HomeScreen` (Task 4) and every later phase's screens for the auth header.

- [ ] **Step 1: Create `mobile/api/auth.js`**

```js
import { request } from './client';

export function login(correo_electronico, password) {
  return request('/auth/login', {
    method: 'POST',
    body: { correo_electronico, password },
    auth: false,
  });
}
```

- [ ] **Step 1b: Create `mobile/navigationRef.js`**

```js
import { createNavigationContainerRef } from '@react-navigation/native';

export const navigationRef = createNavigationContainerRef();
```

React Navigation 7 ya trae esto — no hay dependencia nueva. Es la pieza que
permite a `AuthContext` mandar al usuario a Login desde fuera de un
componente cuando la API responde 401.

- [ ] **Step 2: Create `mobile/auth/AuthContext.js`**

```js
import React, { createContext, useContext, useEffect, useState } from 'react';
import { getToken, saveToken, clearToken, decodeToken } from './session';
import { login as loginRequest } from '../api/auth';
import { setUnauthorizedHandler } from '../api/client';
import { navigationRef } from '../navigationRef';

const AuthContext = createContext(null);
const SIN_SESION = { token: null, rol: null, userId: null, loading: false };

export function AuthProvider({ children }) {
  const [session, setSession] = useState({ ...SIN_SESION, loading: true });

  useEffect(() => {
    (async () => {
      const token = await getToken();
      const payload = token ? decodeToken(token) : null;
      // token presente pero vencido == sin sesión; no esperamos al primer 401
      const vigente = payload && payload.exp && payload.exp * 1000 > Date.now();
      if (vigente) {
        setSession({ token, rol: payload.rol, userId: payload.user_id, loading: false });
      } else {
        if (token) await clearToken();
        setSession(SIN_SESION);
      }
    })();
  }, []);

  useEffect(() => {
    // client.js avisa aquí en cualquier 401: limpiamos estado y volvemos a Login.
    setUnauthorizedHandler(async () => {
      await clearToken();
      setSession(SIN_SESION);
      if (navigationRef.isReady()) {
        navigationRef.resetRoot({ index: 0, routes: [{ name: 'Login' }] });
      }
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const login = async (correo, password) => {
    const { access_token, rol } = await loginRequest(correo, password);
    await saveToken(access_token);
    const payload = decodeToken(access_token);
    setSession({ token: access_token, rol, userId: payload.user_id, loading: false });
    return rol;
  };

  const logout = async () => {
    await clearToken();
    setSession(SIN_SESION);
  };

  return (
    <AuthContext.Provider value={{ ...session, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
```

- [ ] **Step 3: Rewrite the `login()` function in `mobile/screens/LoginScreen.js`**

Replace lines 1-44 (imports through the end of the `login` function) with:

```js
import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  Image,
  KeyboardAvoidingView,
  ScrollView,
  Platform
} from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { ApiError } from '../api/client';

export default function LoginScreen({ navigation }) {

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleLogin = async () => {
    setError('');

    if (!email.trim() || !password.trim()) {
      setError('Faltan campos');
      return;
    }

    if (!email.includes('@')) {
      setError('Correo inválido');
      return;
    }

    setLoading(true);
    try {
      await login(email.trim(), password);
      navigation.replace('Home');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  };
```

Then, in the JSX (the part that stays unchanged below), remove the entire role-picker block (`<Text style={styles.label}>rol: {rol}</Text>` through the closing `</View>` of `styles.roles`, originally lines 83-103) since role now comes from the JWT, not a manual picker. Add an error message display and wire the button to `handleLogin`:

```jsx
        <View style={styles.card}>

          <TextInput
            placeholder="correo electrónico"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            style={styles.input}
          />

          <TextInput
            placeholder="contraseña"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            style={styles.input}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
            <Text style={styles.buttonText}>{loading ? 'Ingresando...' : 'Iniciar sesión'}</Text>
          </TouchableOpacity>

        </View>
```

Add one style to the existing `StyleSheet.create` block:

```js
  error: {
    color: '#C0392B',
    marginBottom: 10,
    textAlign: 'center',
  },
```

The `rol` variable, `roles`, `role`, `selected` styles become unused — remove the now-dead `roles`/`role`/`selected` entries from `StyleSheet.create` along with the JSX block above (dead style objects left behind would be confusing, not because they cause a bug).

- [ ] **Step 3b: Make `mobile/screens/SplashScreen.js` respect the restored session**

Replace lines 1-10 with:

```js
import React, { useEffect } from 'react';
import { View, Text, StyleSheet, Image, ActivityIndicator } from 'react-native';
import { useAuth } from '../auth/AuthContext';

export default function SplashScreen({ navigation }) {
  const { token, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    navigation.replace(token ? 'Home' : 'Login');
  }, [loading, token, navigation]);
```

(el JSX y los estilos del resto del archivo quedan intactos).

Antes, el `setTimeout(... 'Login', 2000)` incondicional hacía que restaurar la
sesión desde SecureStore fuera código muerto: siempre se aterrizaba en Login
aunque hubiera token válido, y `AuthContext.loading` se producía sin que nadie
lo consumiera. El `setTimeout` fijo desaparece: el splash dura exactamente lo
que tarda la lectura de SecureStore.

- [ ] **Step 4: Wrap navigation in `AuthProvider` in `mobile/App.js`**

Change:

```js
export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Splash">
```

to:

```js
import { AuthProvider } from './auth/AuthContext';
import { navigationRef } from './navigationRef';

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer ref={navigationRef}>
        <Stack.Navigator initialRouteName="Splash">
```

and close the added `</AuthProvider>` right after the existing closing `</NavigationContainer>` (`App.js:102-103`).

- [ ] **Step 5: Manual verification**

Run `npx expo start` in `mobile/`, open in Expo Go, log in with
`mesero@coffeecode.com` / `Mesero123!`. Expected: navigates to Home. Try a
wrong password: expected inline red error text, no crash, no `alert()`.
Then: kill the app and reopen it — expected to land **directly on Home**
(session restored from SecureStore), not on Login. Finally, tap "Cerrar
sesión", kill and reopen: expected Login.

- [ ] **Step 6: Commit**

```bash
git add mobile/api/auth.js mobile/auth/AuthContext.js mobile/screens/LoginScreen.js mobile/App.js
git commit -m "feat(mobile): login real contra la API con JWT"
```

---

### Task 4: Home screen role filter

**Files:**
- Modify: `mobile/screens/HomeScreen.js` (full rewrite — replaces the always-show-3-buttons layout with a role-filtered list)

**Interfaces:**
- Consumes: `useAuth()` from `auth/AuthContext.js` (Task 3) for `rol`.

- [ ] **Step 1: Rewrite `mobile/screens/HomeScreen.js`**

```js
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useAuth } from '../auth/AuthContext';

const BOTONES_POR_ROL = {
  Mesero: [{ label: 'Mesero', target: 'Mesas' }],
  Cocinero: [{ label: 'Cocina', target: 'Cocina' }],
  Cajero: [{ label: 'Caja', target: 'Caja' }],
  Administrador: [
    { label: 'Mesero', target: 'Mesas' },
    { label: 'Cocina', target: 'Cocina' },
    { label: 'Caja', target: 'Caja' },
  ],
};

export default function HomeScreen({ navigation }) {
  const { rol, logout } = useAuth();
  const botones = BOTONES_POR_ROL[rol] || [];

  const handleLogout = async () => {
    await logout();
    navigation.replace('Login');
  };

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Coffee Code</Text>
      <Text style={styles.subtitle}>Panel principal ({rol})</Text>

      {botones.map((boton) => (
        <TouchableOpacity
          key={boton.target}
          style={styles.button}
          onPress={() => navigation.navigate(boton.target)}
        >
          <Text style={styles.text}>{boton.label}</Text>
        </TouchableOpacity>
      ))}

      <TouchableOpacity style={styles.logout} onPress={handleLogout}>
        <Text style={styles.logoutText}>Cerrar sesión</Text>
      </TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    justifyContent: 'center',
    padding: 20
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 5
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 30,
    color: 'gray'
  },
  button: {
    backgroundColor: '#2E1B0F',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15
  },
  text: {
    color: 'white',
    fontSize: 18,
    textAlign: 'center'
  },
  logout: {
    marginTop: 20,
    padding: 10,
  },
  logoutText: {
    color: '#C0392B',
    textAlign: 'center',
  },
});
```

- [ ] **Step 2: Manual verification**

Log in as `mesero@coffeecode.com`. Expected: Home shows only the "Mesero" button (not Caja/Cocina). Tap "Cerrar sesión", expected: returns to Login and a repeat login is required (token cleared).

- [ ] **Step 3: Commit**

```bash
git add mobile/screens/HomeScreen.js
git commit -m "feat(mobile): Home filtra botones por rol y agrega logout"
```

---

### Task 5: Mesas screen — real grid from `GET /mesas`

**Files:**
- Create: `mobile/api/mesas.js`
- Modify: `mobile/screens/MesasScreen.js` (full replacement — this file currently contains a broken duplicate of `EstadoPedidoScreen`'s mock content; it is rewritten from scratch as a mesa-selector grid)

**Interfaces:**
- Consumes: `request` from `api/client.js` (Task 2), `getPedidoActivoDeMesa` from `api/pedidos.js` (Task 6 — this task's Step 2 imports it, so Task 6's Step 2 must land first or the import is added at that point).
- Produces: `getMesas(): Promise<Array<{id, numero_mesa, capacidad, activo, estatus:{id,nombre}}>>`. `MesasScreen` navigates to `Pedido` with `{mesaId, numeroMesa}` when the mesa is free, or to `Detalle` with `{pedidoId, numeroMesa}` when it's already Ocupada — consumed by Tasks 6 and 7.

> Sequencing note for the implementing agent: move Task 6's Step 2 (`api/pedidos.js`) **before** Task 5 Step 2, or create `api/pedidos.js` early. The order in the file is otherwise unchanged.

- [ ] **Step 1: Create `mobile/api/mesas.js`**

```js
import { request } from './client';

export function getMesas() {
  return request('/mesas');
}
```

- [ ] **Step 2: Replace `mobile/screens/MesasScreen.js` entirely**

```js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getMesas } from '../api/mesas';
import { getPedidoActivoDeMesa } from '../api/pedidos';
import { ApiError } from '../api/client';

const COLOR_POR_ESTATUS = {
  Libre: '#27AE60',
  Ocupada: '#C0392B',
  Reservada: '#E67E22',
};

export default function MesasScreen({ navigation }) {
  const [mesas, setMesas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [abriendo, setAbriendo] = useState(null);
  const [error, setError] = useState('');

  const cargarMesas = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getMesas();
      setMesas(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargarMesas();
    }, [cargarMesas])
  );

  const abrirMesa = async (mesa) => {
    setError('');
    const nuevoPedido = () =>
      navigation.navigate('Pedido', { mesaId: mesa.id, numeroMesa: mesa.numero_mesa });

    if (mesa.estatus.nombre !== 'Ocupada') {
      nuevoPedido();
      return;
    }

    // Mesa ocupada: se vuelve al pedido que ya existe, NO se crea otro.
    setAbriendo(mesa.id);
    try {
      const activo = await getPedidoActivoDeMesa(mesa.id);
      if (activo) {
        navigation.navigate('Detalle', { pedidoId: activo.id, numeroMesa: mesa.numero_mesa });
      } else {
        // Ocupada sin pedido activo (estado inconsistente en DB): dejar crear uno.
        nuevoPedido();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo abrir la mesa');
    } finally {
      setAbriendo(null);
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
      <Text style={styles.title}>Mesas</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={mesas}
        keyExtractor={(item) => item.id.toString()}
        numColumns={2}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.card, { borderColor: COLOR_POR_ESTATUS[item.estatus.nombre] || '#999' }]}
            onPress={() => abrirMesa(item)}
            disabled={abriendo !== null}
          >
            <Text style={styles.mesaNumero}>Mesa {item.numero_mesa}</Text>
            <Text style={{ color: COLOR_POR_ESTATUS[item.estatus.nombre] || '#999', fontWeight: 'bold' }}>
              {item.estatus.nombre}
            </Text>
            <Text style={styles.capacidad}>Capacidad: {item.capacidad}</Text>
            {abriendo === item.id ? <Text style={styles.capacidad}>Abriendo…</Text> : null}
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5', padding: 15 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 15, textAlign: 'center' },
  error: { color: '#C0392B', textAlign: 'center', marginBottom: 10 },
  card: {
    flex: 1,
    backgroundColor: 'white',
    margin: 6,
    padding: 15,
    borderRadius: 12,
    borderWidth: 2,
    elevation: 3,
  },
  mesaNumero: { fontSize: 18, fontWeight: 'bold', marginBottom: 4 },
  capacidad: { color: 'gray', marginTop: 4 },
});
```

**Por qué la rama.** El backend no impide crear un segundo pedido en una mesa
ocupada: `crear_pedido` (`api/app/services/pedidos.py:45-48`) solo valida
`Mesa.activo`. Sin esta rama, tocar una mesa Ocupada abría el formulario de
alta y duplicaba el pedido — y el Mesero no tenía **ningún** camino para
volver a un pedido en curso.

- [ ] **Step 3: Manual verification**

Log in as Mesero, tap "Mesero" on Home. Expected: grid of 8 mesa cards (seed creates mesas 1-8), all showing "Libre" in green initially. Confirm against `GET /mesas` via Postman/curl that the count and estatus match.

Then test the branch: create a pedido on one mesa (Task 6 must be done for
this), go back to Mesas — that mesa is now "Ocupada" in red. Tap it. Expected:
lands on `Detalle` with the existing pedido, **not** on the new-order form.
Confirm via `GET /pedidos` that no second pedido was created for that mesa.

- [ ] **Step 4: Commit**

```bash
git add mobile/api/mesas.js mobile/screens/MesasScreen.js
git commit -m "feat(mobile): MesasScreen real, reemplaza el duplicado roto"
```

---

### Task 6: Pedido screen — real menu + `POST /pedidos`

**Files:**
- Create: `mobile/api/productos.js`
- Create: `mobile/api/pedidos.js`
- Modify: `mobile/screens/PedidoScreen.js` (full replacement — mock menu and mock `guardarPedido` replaced with real API calls)

**Interfaces:**
- Consumes: `request` from `api/client.js`, `mesaId` from `route.params` (produced by Task 5's `MesasScreen`), `userId` from `useAuth()` (Task 3).
- Produces: `getProductos(): Promise<Array<{id, nombre, precio_venta, ...}>>`, `crearPedido({mesaId, usuarioId, items}): Promise<PedidoOut>`, `getPedido(id): Promise<PedidoOut>`. `getPedido` and the `PedidoOut` shape are consumed by Task 7's `DetalleScreen`.

- [ ] **Step 1: Create `mobile/api/productos.js`**

```js
import { request } from './client';

export function getProductos() {
  return request('/productos');
}
```

- [ ] **Step 2: Create `mobile/api/pedidos.js`**

```js
import { request } from './client';

// Estados en los que un pedido sigue "vivo" — espejo de
// ESTATUS_PEDIDO_ACTIVOS en api/app/core/constants.py:43-47
const ESTADOS_ACTIVOS = ['Pendiente', 'En preparación', 'Listo'];

export function crearPedido({ mesaId, usuarioId, items }) {
  return request('/pedidos', {
    method: 'POST',
    body: {
      mesa_id: mesaId,
      usuario_id: usuarioId,
      items: items.map((item) => ({
        id_producto: item.id_producto,
        cantidad: item.cantidad,
        especificaciones: item.especificaciones || null,
      })),
    },
  });
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

// GET /pedidos no filtra por mesa; se piden los tres estados activos y se
// filtra client-side. Mesero tiene permiso de lectura sobre GET /pedidos
// (api/app/routers/pedidos.py:39-49). Devuelve el más reciente (la API ordena
// por fecha ascendente) o null.
export async function getPedidoActivoDeMesa(mesaId) {
  const listas = await Promise.all(
    ESTADOS_ACTIVOS.map((estado) => request(`/pedidos?estado=${encodeURIComponent(estado)}`))
  );
  const activos = listas.flat().filter((p) => p.id_mesa === mesaId);
  return activos.length ? activos[activos.length - 1] : null;
}
```

- [ ] **Step 3: Replace `mobile/screens/PedidoScreen.js` entirely**

```js
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { getProductos } from '../api/productos';
import { crearPedido } from '../api/pedidos';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export default function PedidoScreen({ route, navigation }) {
  const { mesaId, numeroMesa } = route.params;
  const { userId } = useAuth();

  const [menu, setMenu] = useState([]);
  const [pedido, setPedido] = useState([]);
  const [loadingMenu, setLoadingMenu] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const productos = await getProductos();
        // GET /productos solo filtra por `activo`; los `disponible:false`
        // llegan igual y provocarían un 409 tardío al Guardar
        // (api/app/services/pedidos.py:64-71). Se filtran aquí.
        setMenu(productos.filter((p) => p.disponible !== false));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'No se pudo cargar el menú');
      } finally {
        setLoadingMenu(false);
      }
    })();
  }, []);

  const agregarProducto = (producto) => {
    setPedido((actual) => {
      const existe = actual.find((p) => p.id_producto === producto.id);
      if (existe) {
        return actual.map((p) =>
          p.id_producto === producto.id ? { ...p, cantidad: p.cantidad + 1 } : p
        );
      }
      return [...actual, { id_producto: producto.id, nombre: producto.nombre, cantidad: 1 }];
    });
  };

  const guardarPedido = async () => {
    if (pedido.length === 0) {
      setError('El pedido no puede estar vacío');
      return;
    }

    setGuardando(true);
    setError('');
    try {
      const creado = await crearPedido({ mesaId, usuarioId: userId, items: pedido });
      navigation.navigate('Detalle', { pedidoId: creado.id, numeroMesa });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el pedido');
    } finally {
      setGuardando(false);
    }
  };

  if (loadingMenu) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Mesa {numeroMesa ?? mesaId}</Text>

      <Text style={styles.subtitle}>Pedido actual</Text>
      {pedido.length === 0 ? (
        <Text style={{ color: 'gray' }}>Sin productos aún</Text>
      ) : (
        pedido.map((item) => (
          <Text key={item.id_producto}>{item.nombre} x{item.cantidad}</Text>
        ))
      )}

      <Text style={styles.subtitle}>Menú</Text>

      <FlatList
        data={menu}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.item} onPress={() => agregarProducto(item)}>
            <Text>{item.nombre} — ${item.precio_venta}</Text>
            <Text style={{ fontWeight: 'bold' }}>+</Text>
          </TouchableOpacity>
        )}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity style={styles.button} onPress={guardarPedido} disabled={guardando}>
        <Text style={{ color: 'white', fontWeight: 'bold' }}>
          {guardando ? 'Guardando...' : '✔ Guardar / Finalizar pedido'}
        </Text>
      </TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 24, fontWeight: 'bold', textAlign: 'center' },
  subtitle: { marginTop: 15, fontSize: 16, fontWeight: 'bold' },
  error: { color: '#C0392B', marginTop: 10, textAlign: 'center' },
  item: {
    padding: 15,
    backgroundColor: '#eee',
    marginVertical: 5,
    borderRadius: 10,
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  button: {
    backgroundColor: '#2E1B0F',
    padding: 12,
    borderRadius: 10,
    marginTop: 20,
    alignItems: 'center'
  }
});
```

> `mesaId` es la PK de la tabla, no el número de mesa visible
> (`MesaOut.numero_mesa`); coinciden solo por el orden del seed.

- [ ] **Step 4: Manual verification**

Tap any "Libre" mesa card. Expected: real product menu loads (Café Americano, Espresso, Capuchino, etc. from seed data, not the old 4-item mock). Add 2 items, tap "Guardar". Expected: navigates forward (Task 7's screen, still a stub at this point — confirm no crash) and a new row exists in `GET /pedidos` via curl/Postman with the correct `mesa_id`/`items`.

- [ ] **Step 5: Commit**

```bash
git add mobile/api/productos.js mobile/api/pedidos.js mobile/screens/PedidoScreen.js
git commit -m "feat(mobile): PedidoScreen crea pedidos reales contra la API"
```

---

### Task 7: Merge EstadoPedido + DetallePedido into one real Detalle screen

**Files:**
- Create: `mobile/screens/DetalleScreen.js`
- Delete: `mobile/screens/EstadoPedidoScreen.js` (mock content fully superseded)
- Delete: `mobile/screens/DetallePedidoScreen.js` (was orphaned/unregistered — its state-machine buttons are superseded by the single, backend-accurate "Marcar como Entregado" action built into `DetalleScreen` below)
- Modify: `mobile/App.js` (remove `EstadoPedidoScreen` import/route, add `DetalleScreen` import/route, remove `RecuperarPassword` unused import check — leave `RecuperarPassword` route registered since deleting it is out of this plan's scope, it's just unreachable from Login)
- Modify: `mobile/screens/ColaPedidosScreen.js:31` (one-line fix: `navigation.navigate('EstadoPedido', ...)` → `navigation.navigate('Detalle', { pedidoId: item.id })` — only a compatibility fix so tapping "Ver preparación" doesn't crash after the route rename; Fase 2 rewires this screen's data source properly)

**Interfaces:**
- Consumes: `getPedido(id)` from `api/pedidos.js` (Task 6), `pedidoId` route param (produced by Task 6's `PedidoScreen`).

- [ ] **Step 1: Create `mobile/screens/DetalleScreen.js`**

```js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido, cambiarEstadoPedido } from '../api/pedidos';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export default function DetalleScreen({ route }) {
  const { pedidoId, numeroMesa } = route.params;
  const { rol } = useAuth();
  const [pedido, setPedido] = useState(null);
  const [loading, setLoading] = useState(true);
  const [entregando, setEntregando] = useState(false);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getPedido(pedidoId);
      setPedido(data);
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

  const marcarEntregado = async () => {
    setEntregando(true);
    setError('');
    try {
      setPedido(await cambiarEstadoPedido(pedidoId, 'Entregado'));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo marcar como entregado');
    } finally {
      setEntregando(false);
    }
  };

  if (loading && !pedido) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  if (error && !pedido) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error}</Text>
        <TouchableOpacity style={styles.button} onPress={cargar}>
          <Text style={styles.buttonText}>Reintentar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const puedeEntregar =
    (rol === 'Mesero' || rol === 'Administrador') && pedido.estatus.nombre === 'Listo';

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>

      <Text style={styles.title}>Pedido #{pedido.id} — Mesa {numeroMesa ?? pedido.id_mesa}</Text>
      <Text style={styles.estado}>Estado: {pedido.estatus.nombre}</Text>

      {pedido.detalle.map((item) => (
        <View key={item.id} style={styles.card}>
          <Text style={styles.producto}>{item.producto.nombre} x{item.cantidad}</Text>
          <Text>${item.precio_unitario} c/u</Text>
          <Text style={{ color: '#E67E22' }}>{item.estatus.nombre}</Text>
        </View>
      ))}

      {pedido.total !== null && (
        <Text style={styles.total}>Total: ${pedido.total}</Text>
      )}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {puedeEntregar && (
        <TouchableOpacity style={styles.entregar} onPress={marcarEntregado} disabled={entregando}>
          <Text style={styles.buttonText}>
            {entregando ? 'Actualizando...' : 'Marcar como Entregado'}
          </Text>
        </TouchableOpacity>
      )}

      <TouchableOpacity style={styles.button} onPress={cargar}>
        <Text style={styles.buttonText}>Actualizar</Text>
      </TouchableOpacity>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  estado: { fontSize: 16, fontWeight: 'bold', color: '#E67E22', marginBottom: 15 },
  error: { color: '#C0392B', marginBottom: 15, textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 15, borderRadius: 12, marginBottom: 10, elevation: 3 },
  producto: { fontSize: 16, fontWeight: 'bold' },
  total: { fontSize: 18, fontWeight: 'bold', marginTop: 10, marginBottom: 20 },
  entregar: { backgroundColor: '#27AE60', padding: 14, borderRadius: 10, alignItems: 'center', marginBottom: 10 },
  button: { backgroundColor: '#2E1B0F', padding: 14, borderRadius: 10, alignItems: 'center' },
  buttonText: { color: 'white', fontWeight: 'bold' },
});
```

**Por qué existe este botón** (la spec anterior afirmaba lo contrario y estaba
mal): `PUT /pedidos/{id}/estado` acepta el rol `Mesero`
(`api/app/routers/pedidos.py:70-79`), y desde `Listo` la única transición no
destructiva es `Entregado` (`api/app/core/constants.py:38`). Esa transición es
además la que **libera la mesa**
(`api/app/services/pedidos.py:175-177` → `_liberar_mesa_si_no_hay_pedidos_activos`).
Sin este botón ningún pedido sale nunca de `Listo`: la mesa queda Ocupada para
siempre, la cola de Caja crece sin límite (ver Fase 3) y el paso 07 de
`fuego-flujo-pedido-completo` ("Mesero entrega y la mesa se libera") no tiene
equivalente en la app.

`Cancelado` (también válido desde `Listo`) **no** se implementa en móvil —
decisión de alcance explícita, ver la sección de brechas conocidas de la spec.

- [ ] **Step 2: Delete the two superseded files**

```bash
git rm mobile/screens/EstadoPedidoScreen.js mobile/screens/DetallePedidoScreen.js
```

- [ ] **Step 3: Update `mobile/App.js`**

Remove line 10 (`import EstadoPedidoScreen from './screens/EstadoPedidoScreen';`), add `import DetalleScreen from './screens/DetalleScreen';` in its place. Remove the `EstadoPedido` `<Stack.Screen>` block (originally lines 56-59) and add:

```jsx
        <Stack.Screen
          name="Detalle"
          component={DetalleScreen}
        />
```

- [ ] **Step 4: Fix the dead nav target in `mobile/screens/ColaPedidosScreen.js:31`**

Change:

```js
onPress={() => navigation.navigate('EstadoPedido', { pedido: item })}
```

to:

```js
onPress={() => navigation.navigate('Detalle', { pedidoId: item.id })}
```

This is a compatibility fix only — `ColaPedidosScreen` still uses mock data (`item.id` is `1`/`2`/`3` from the hardcoded array, not a real pedido id) and will be fully rewired in the Fase 2 (Cocina) plan. This step just prevents a broken-route crash if someone taps "Ver preparación" before Fase 2 lands.

- [ ] **Step 5: Manual verification — full Mesero flow end-to-end**

1. `docker compose up -d` in `api/` (fresh or existing containers), confirm `alembic upgrade head` is applied.
2. In `mobile/`, run `npx expo start`, open in Expo Go on a phone on the same LAN.
3. Log in as `mesero@coffeecode.com` / `Mesero123!`.
4. Tap a "Libre" mesa, add 2 different products, tap "Guardar / Finalizar pedido".
5. Expected: navigates to the Detalle screen showing the correct **numero de
   mesa** (el que se ve en el grid, no la PK), both items with correct
   quantities/prices, estatus "Pendiente". No aparece el botón "Marcar como
   Entregado" (el pedido no está en `Listo`).
6. Confirm via `GET /pedidos/{id}` (Postman/curl with the Mesero token) that
   the API's data matches exactly what the screen shows.
7. Confirm via `GET /mesas` that the mesa used is now "Ocupada".
8. Go back to Mesas and tap that same (now Ocupada) mesa. Expected: lands on
   `Detalle` del mismo pedido. Confirm via `GET /pedidos` que **no** se creó
   un segundo pedido para esa mesa.
9. With Postman (Cocinero token) move the pedido `Pendiente → En preparación →
   Listo`. Back on `Detalle`, tap "Actualizar". Expected: aparece el botón
   verde "Marcar como Entregado". Tap it. Expected: estatus pasa a `Entregado`
   y `GET /mesas` muestra esa mesa **"Libre"** de nuevo.
10. Confirm que el botón NO aparece para un pedido en `Pendiente` ni `En
    preparación`, y que un producto con `disponible=false` (ponlo así vía
    `PUT /productos/{id}`) **no** se lista en el menú de `PedidoScreen`.

- [ ] **Step 6: Commit**

```bash
git add mobile/screens/DetalleScreen.js mobile/App.js mobile/screens/ColaPedidosScreen.js
git commit -m "feat(mobile): fusiona EstadoPedido+DetallePedido en DetalleScreen real, elimina duplicados"
```

---

## Fase 0 complete when

All 7 tasks committed, Task 7 Step 5's full end-to-end manual verification passes against the live Docker API. `api/client.js`, `auth/session.js`, `auth/AuthContext.js` are stable — Fase 2 and Fase 3 plans build on top without modifying these three files.
