# Mobile Fase 4 — WebSocket Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real-time push updates (no manual pull-to-refresh needed) to the three role screens, using the backend's existing raw WebSocket channels.

**Architecture:** One shared `ws/client.js` opens a raw `WebSocket` to `{WS_URL}/ws/{canal}?token={jwt}` (backend channels: `mesero`, `cocina`, `caja` — see `api/app/routers/websockets.py`). Each screen subscribes on focus, unsubscribes on blur, and re-runs its existing REST fetch when a relevant event arrives — no new state model, just an event-triggered refresh of what Fases 0-2-3 already built.

**Tech Stack:** React Native's built-in `WebSocket` global (no `socket.io-client`, no new dependency).

## Global Constraints

- **Prerequisite: this plan runs LAST**, after Fase 0, Fase 2 (Cocina), and Fase 3 (Caja) are all merged to `main` — it touches `DetalleScreen.js` (Fase 0), `ColaPedidosScreen.js` (Fase 2), and `CajaScreen.js` (Fase 3) in the same plan, so it cannot run in a parallel worktree with any of them.
- Backend event contract (from `api/app/routers/websockets.py` / `api/app/services/pedidos.py`, already verified against running code):
  - channel `cocina` receives `{"evento":"nuevo_pedido","pedido_id","mesa_id"}` when a pedido is created.
  - channel `mesero` + `caja` receive `{"evento":"pedido_activado","pedido_id","mesa_id"}` when a pedido moves to "En preparación".
  - channel `mesero` receives `{"evento":"pedido_listo","pedido_id","mesa_id","alertas_stock_bajo":[...]}` when a pedido moves to "Listo".
  - Auth: token passed as a query param (`?token=<jwt>`), not a header (WebSocket API can't set custom headers in RN). Server closes with code 1008 on invalid/expired token or role mismatch.
- No axios, no socket.io — plain `WebSocket` global, already available in React Native without a polyfill.
- No new test framework — manual verification against the live Docker API and its real WS server.

---

### Task 1: Shared WebSocket client

**Files:**
- Modify: `mobile/config.js` (add `WS_URL` export alongside the existing `API_URL`)
- Create: `mobile/ws/client.js`

**Interfaces:**
- Consumes: `getToken()` from `auth/session.js`.
- Produces: `connectToChannel(canal, {onMessage, onError}): Promise<() => void>` — resolves to an unsubscribe/close function. Consumed by Task 2, 3, 4.

- [ ] **Step 1: Add `WS_URL` to `mobile/config.js`**

Append to the existing file:

```js
export const WS_URL = API_URL.replace(/^http/, 'ws');
```

- [ ] **Step 2: Create `mobile/ws/client.js`**

```js
import { WS_URL } from '../config';
import { getToken } from '../auth/session';

export async function connectToChannel(canal, { onMessage, onError } = {}) {
  const token = await getToken();
  if (!token) {
    return () => {};
  }

  const socket = new WebSocket(`${WS_URL}/ws/${canal}?token=${token}`);

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onMessage) onMessage(data);
    } catch (err) {
      // frame no era JSON válido, se ignora
    }
  };

  socket.onerror = (event) => {
    if (onError) onError(event);
  };

  return () => {
    socket.close();
  };
}
```

- [ ] **Step 3: Manual verification**

With the API's Docker stack running, from any JS console or a throwaway snippet, confirm a raw connection works before wiring screens:

```bash
# requires a valid JWT for a Mesero user, obtained via /auth/login
wscat -c "ws://<LAN_IP>:8000/ws/mesero?token=<JWT>"
```

(If `wscat` isn't installed: `npm install -g wscat`.) Expected: connection stays open (no immediate 1008 close). Trigger a pedido → "Listo" transition from another terminal/Postman and confirm the `pedido_listo` JSON frame arrives in the `wscat` session.

- [ ] **Step 4: Commit**

```bash
git add mobile/config.js mobile/ws/client.js
git commit -m "feat(mobile): cliente WebSocket compartido para canales mesero/cocina/caja"
```

---

### Task 2: Mesero — live `pedido_listo` on `DetalleScreen`

**Files:**
- Modify: `mobile/screens/DetalleScreen.js` (adds a WS subscription alongside the existing `useFocusEffect` REST fetch; no removal of the manual "Actualizar" button — WS is additive, manual refresh stays as a fallback)

**Interfaces:**
- Consumes: `connectToChannel('mesero', ...)` from `ws/client.js` (Task 1).

- [ ] **Step 1: Add the WS subscription to `mobile/screens/DetalleScreen.js`**

Add the import:

```js
import { connectToChannel } from '../ws/client';
```

Add a second effect alongside the existing `useFocusEffect(() => { cargar(); }, [cargar])`:

```js
  useFocusEffect(
    useCallback(() => {
      let cerrar = () => {};
      connectToChannel('mesero', {
        onMessage: (evento) => {
          if (evento.evento === 'pedido_listo' && evento.pedido_id === pedido?.id) {
            cargar();
          }
        },
      }).then((unsub) => {
        cerrar = unsub;
      });

      return () => cerrar();
    }, [pedido?.id, cargar])
  );
```

(Place this as a second `useFocusEffect` call in the component, after the existing one — React Navigation supports multiple `useFocusEffect` hooks in the same component.)

- [ ] **Step 2: Manual verification**

Open `DetalleScreen` for a pedido that's currently "En preparación" (stay on the screen, don't tap "Actualizar"). From Cocina (another device/session, or Postman with a Cocinero token), mark that pedido "Listo". Expected: within ~2 seconds the screen updates to show "Listo" without the user tapping "Actualizar".

- [ ] **Step 3: Commit**

```bash
git add mobile/screens/DetalleScreen.js
git commit -m "feat(mobile): DetalleScreen se actualiza en vivo al recibir pedido_listo"
```

---

### Task 3: Cocina — live `nuevo_pedido` on `ColaPedidosScreen`

**Files:**
- Modify: `mobile/screens/ColaPedidosScreen.js` (adds a WS subscription alongside the existing `useFocusEffect` REST fetch)

**Interfaces:**
- Consumes: `connectToChannel('cocina', ...)` from `ws/client.js` (Task 1).

- [ ] **Step 1: Add the WS subscription to `mobile/screens/ColaPedidosScreen.js`**

Add the import:

```js
import { connectToChannel } from '../ws/client';
```

Add a second `useFocusEffect`:

```js
  useFocusEffect(
    useCallback(() => {
      let cerrar = () => {};
      connectToChannel('cocina', {
        onMessage: (evento) => {
          if (evento.evento === 'nuevo_pedido') {
            cargar();
          }
        },
      }).then((unsub) => {
        cerrar = unsub;
      });

      return () => cerrar();
    }, [cargar])
  );
```

- [ ] **Step 2: Manual verification**

Leave `ColaPedidosScreen` open as Cocinero. From another session (Mesero app or Postman), create a new pedido. Expected: within ~2 seconds the new pedido appears in the cola without navigating away and back.

- [ ] **Step 3: Commit**

```bash
git add mobile/screens/ColaPedidosScreen.js
git commit -m "feat(mobile): ColaPedidosScreen se actualiza en vivo al recibir nuevo_pedido"
```

---

### Task 4: Caja — live queue refresh on `pedido_activado`

**Files:**
- Modify: `mobile/screens/CajaScreen.js` (adds a WS subscription alongside the existing `useFocusEffect` REST fetch)

**Interfaces:**
- Consumes: `connectToChannel('caja', ...)` from `ws/client.js` (Task 1).

- [ ] **Step 1: Add the WS subscription to `mobile/screens/CajaScreen.js`**

Add the import:

```js
import { connectToChannel } from '../ws/client';
```

Add a second `useFocusEffect`:

```js
  useFocusEffect(
    useCallback(() => {
      let cerrar = () => {};
      connectToChannel('caja', {
        onMessage: (evento) => {
          if (evento.evento === 'pedido_activado') {
            cargar();
          }
        },
      }).then((unsub) => {
        cerrar = unsub;
      });

      return () => cerrar();
    }, [cargar])
  );
```

Note: `pedido_activado` fires when a pedido enters "En preparación", earlier than the "Listo" state `CajaScreen` actually queues on — this event is a proxy signal that new activity is happening, not a precise "your queue changed" signal. It's wired here because it's the only `caja`-channel event the backend emits (per `api/app/routers/websockets.py`); it keeps the screen reasonably fresh without polling. The existing `useFocusEffect` REST fetch remains the authoritative refresh on screen focus.

- [ ] **Step 2: Manual verification**

Leave `CajaScreen` open as Cajero. From Cocina, move some pedido to "En preparación". Expected: `CajaScreen` re-fetches (no visible change expected unless the Listo queue actually changed, but confirm via a console log or a temporary visual indicator that `cargar()` ran) without a crash or duplicate-request pile-up.

- [ ] **Step 3: Commit**

```bash
git add mobile/screens/CajaScreen.js
git commit -m "feat(mobile): CajaScreen escucha pedido_activado para refrescar la cola"
```

---

## Fase 4 complete when

All 4 tasks committed, each manual verification step confirms a live WS push (not just the pre-existing REST fetch) updates the corresponding screen within ~2 seconds, matching the project's non-functional requirement (`CLAUDE.md`: "Notificaciones WS < 2s").
