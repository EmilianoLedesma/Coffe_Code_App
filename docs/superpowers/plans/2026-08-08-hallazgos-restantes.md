# Hallazgos restantes de la prueba en dispositivo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar los 9 hallazgos restantes de la prueba en dispositivo real (#1, #5, #6, #7, #8, #9, #10, #13, #14) — labels, WS faltante, validaciones, edición de producto, CRUD de recetas, total real antes de cobrar, fix de fechas en reportes, cálculo automático de compra, filtro de categorías roto.

**Architecture:** Nueve piezas independientes (sin dependencias entre tareas salvo #8 que depende de #7 tocar el mismo archivo `MenuScreen.js`). Backend: un endpoint nuevo (`GET /tickets/{id}`) y un fix de un solo punto (`_rango_por_defecto`). Mobile: retoques a pantallas existentes + una pantalla nueva (`RecetaScreen`).

**Tech Stack:** FastAPI + SQLAlchemy + pytest (backend). React Native + Expo (mobile), sin tests de componente (convención ya establecida del proyecto).

## Global Constraints

- Español en nombres de tablas/campos/mensajes de error/commits.
- Commit tras cada task completa y revisada.
- Sin tests de componente para pantallas React Native (convención ya establecida) — verificación manual contra Docker diferida al usuario.
- Reusar componentes ya existentes (`Card`, `ListItem`, `Chip`, `Input`, `Button`, `Badge`, `EmptyState`) — no crear componentes nuevos salvo que se indique.

---

### Task 1: Label "Mesas" en HomeScreen

**Files:**
- Modify: `mobile/screens/HomeScreen.js:8-16`

**Interfaces:** Ninguna — cambio de texto puro, sin nuevas interfaces.

- [ ] **Step 1: Cambiar el label**

En `mobile/screens/HomeScreen.js`, cambiar las dos ocurrencias de `label: 'Mesero'` (líneas 9 y 13) a `label: 'Mesas'`:

```js
const BOTONES_POR_ROL = {
  Mesero: [{ label: 'Mesas', target: 'Mesas', icon: 'restaurant-outline' }],
  Cocinero: [{ label: 'Cocina', target: 'Cocina', icon: 'flame-outline' }],
  Cajero: [{ label: 'Caja', target: 'Caja', icon: 'cash-outline' }],
  Administrador: [
    { label: 'Mesas', target: 'Mesas', icon: 'restaurant-outline' },
    { label: 'Cocina', target: 'Cocina', icon: 'flame-outline' },
    { label: 'Caja', target: 'Caja', icon: 'cash-outline' },
  ],
};
```

- [ ] **Step 2: Verificación**

Run: `cd mobile && npx jest` — confirma que nada rompe (ningún test referencia este archivo).

- [ ] **Step 3: Commit**

```bash
git add mobile/screens/HomeScreen.js
git commit -m "fix(mobile): boton de Mesero en HomeScreen dice Mesas"
```

---

### Task 2: Tarjeta hero de CocinaScreen — tocable + WebSocket

**Files:**
- Modify: `mobile/screens/CocinaScreen.js`

**Interfaces:**
- Consumes: `connectToChannel` de `mobile/ws/client.js` (mismo patrón usado en `ColaPedidosScreen.js`), `getColaPendientes` de `mobile/api/pedidos_cocina.js` (ya importado).

- [ ] **Step 1: Agregar onPress + WS**

Reemplazar el contenido completo de `mobile/screens/CocinaScreen.js`:

```javascript
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getColaPendientes } from '../api/pedidos_cocina';
import { connectToChannel } from '../ws/client';
import { Card } from '../components/Card';
import { ListItem } from '../components/ListItem';
import { colors, typography, spacing } from '../theme';

export default function CocinaScreen({ navigation }) {
  const [pendientes, setPendientes] = useState(0);

  const cargarPendientes = useCallback(() => {
    getColaPendientes()
      .then((data) => setPendientes(data.length))
      .catch(() => setPendientes(0));
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargarPendientes();
    }, [cargarPendientes])
  );

  useFocusEffect(
    useCallback(() => {
      let cerrar = null;
      let cancelado = false;

      connectToChannel('cocina', {
        onMessage: (evento) => {
          if (evento.evento === 'nuevo_pedido') {
            cargarPendientes();
          }
        },
        onClose: cargarPendientes,
      }).then((unsub) => {
        // la pantalla pudo perder el foco mientras conectábamos
        if (cancelado) {
          unsub();
          return;
        }
        cerrar = unsub;
      });

      return () => {
        cancelado = true;
        if (cerrar) cerrar();
      };
    }, [cargarPendientes])
  );

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Cocina</Text>
      <Text style={styles.subtitle}>Gestión operativa de pedidos</Text>

      <Card size="hero" style={styles.heroCard} onPress={() => navigation.navigate('ColaPedidos')}>
        <Text style={styles.heroNumber}>{pendientes}</Text>
        <Text style={styles.heroLabel}>Pedidos en espera</Text>
      </Card>

      <ListItem
        icon="list-outline"
        title="Cola de pedidos"
        subtitle="Ver y avanzar pedidos pendientes"
        onPress={() => navigation.navigate('ColaPedidos')}
      />

      <ListItem
        icon="restaurant-outline"
        title="Gestión de menú"
        subtitle="Productos y categorías"
        onPress={() => navigation.navigate('Menu')}
      />

      <ListItem
        icon="cube-outline"
        title="Inventario"
        subtitle="Ingredientes y stock"
        onPress={() => navigation.navigate('Inventario')}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, backgroundColor: colors.background },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  subtitle: { color: colors.textSecondary, marginBottom: spacing.lg },
  heroCard: { alignItems: 'center', marginBottom: spacing.xl },
  heroNumber: {
    fontSize: typography.size.hero,
    fontWeight: typography.weight.extrabold,
    color: colors.primary,
  },
  heroLabel: {
    fontSize: typography.size.md,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
});
```

Nota: `Card` ya soporta `onPress` (usado así en `MesasScreen.js`/`PedidosMesaScreen.js` vía `ListItem`, y en el propio `Card` de `MesasScreen.js:88` con `onPress={() => abrirMesa(item)}`) — no hace falta verificar el componente, el patrón ya está probado en el codebase.

- [ ] **Step 2: Verificación**

Run: `cd mobile && npx jest` — confirma que nada rompe.

- [ ] **Step 3: Commit**

```bash
git add mobile/screens/CocinaScreen.js
git commit -m "feat(mobile): tarjeta hero de Cocina tocable y con WebSocket en vivo"
```

---

### Task 3: Validación de unidad + stock inicial en InventarioScreen

**Files:**
- Modify: `mobile/api/ingredientes.js`
- Modify: `mobile/screens/InventarioScreen.js`

**Interfaces:**
- Produces: `createIngrediente({nombre, unidad, stockMinimo, costoUnitario, stockInicial})` — `stockInicial` nuevo parámetro opcional (default `0`).

- [ ] **Step 1: `api/ingredientes.js` — aceptar stock inicial**

```javascript
import { request } from './client';

export function getIngredientes() {
  return request('/ingredientes');
}

export function createIngrediente({ nombre, unidad, stockMinimo, costoUnitario, stockInicial }) {
  return request('/ingredientes', {
    method: 'POST',
    body: {
      nombre,
      unidad,
      stock_actual: stockInicial || 0,
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

- [ ] **Step 2: `InventarioScreen.js` — chips de unidad + campo de stock inicial**

Reemplazar el contenido completo de `mobile/screens/InventarioScreen.js`:

```javascript
import React, { useCallback, useState } from 'react';
import { View, Text, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { getIngredientes, createIngrediente, ajustarStock, deleteIngrediente } from '../api/ingredientes';
import { ApiError } from '../api/client';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { Chip } from '../components/Chip';
import { ListItem } from '../components/ListItem';
import { Badge } from '../components/Badge';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

const UNIDADES = ['g', 'ml', 'u', 'kg', 'l'];

export default function InventarioScreen() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');

  const [nombre, setNombre] = useState('');
  const [unidad, setUnidad] = useState(null);
  const [stockMinimo, setStockMinimo] = useState('');
  const [costoUnitario, setCostoUnitario] = useState('');
  const [stockInicial, setStockInicial] = useState('');

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
    if (!nombre.trim() || !unidad || !stockMinimo || !costoUnitario) {
      setError('Completa nombre, unidad, stock mínimo y costo unitario');
      return;
    }

    setError('');
    try {
      await createIngrediente({
        nombre: nombre.trim(),
        unidad,
        stockMinimo: parseFloat(stockMinimo),
        costoUnitario: parseFloat(costoUnitario),
        stockInicial: stockInicial ? parseFloat(stockInicial) : 0,
      });
      setNombre('');
      setUnidad(null);
      setStockMinimo('');
      setCostoUnitario('');
      setStockInicial('');
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
    setAviso('');
    try {
      const resultado = await deleteIngrediente(id);
      setAviso(resultado.mensaje);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el ingrediente');
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Inventario</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {aviso ? <Text style={styles.aviso}>{aviso}</Text> : null}

      <Input placeholder="Nombre" value={nombre} onChangeText={setNombre} />

      <Text style={styles.label}>Unidad</Text>
      <View style={styles.chipsRow}>
        {UNIDADES.map((u) => (
          <Chip key={u} label={u} selected={unidad === u} onPress={() => setUnidad(u)} />
        ))}
      </View>

      <Input placeholder="Stock mínimo" value={stockMinimo} onChangeText={setStockMinimo} keyboardType="numeric" />
      <Input placeholder="Costo unitario" value={costoUnitario} onChangeText={setCostoUnitario} keyboardType="numeric" />
      <Input placeholder="Stock inicial (opcional)" value={stockInicial} onChangeText={setStockInicial} keyboardType="numeric" />

      <Button variant="secondary" label="Agregar ingrediente" onPress={agregar} />

      <FlatList
        data={items}
        keyExtractor={(i) => i.id.toString()}
        style={styles.list}
        ListEmptyComponent={<EmptyState icon="cube-outline" message="Sin ingredientes registrados." />}
        renderItem={({ item }) => {
          const bajoMinimo = Number(item.stock_actual) < Number(item.stock_minimo);
          return (
            <ListItem
              title={item.nombre}
              subtitle={`Stock: ${item.stock_actual} ${item.unidad} · Mínimo: ${item.stock_minimo} ${item.unidad}`}
              trailing={
                <View style={styles.trailing}>
                  {bajoMinimo ? <Badge label="Bajo mínimo" tone="danger" /> : null}

                  <View style={styles.acciones}>
                    <TouchableOpacity style={styles.iconBtn} onPress={() => subir(item.id)}>
                      <Ionicons name="add-circle-outline" size={24} color={colors.success} />
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.iconBtn} onPress={() => bajar(item.id)}>
                      <Ionicons name="remove-circle-outline" size={24} color={colors.warning} />
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.iconBtn} onPress={() => eliminar(item.id)}>
                      <Ionicons name="trash-outline" size={22} color={colors.danger} />
                    </TouchableOpacity>
                  </View>
                </View>
              }
            />
          );
        }}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  label: { color: colors.textSecondary, marginBottom: spacing.xs, fontSize: typography.size.md },
  error: { color: colors.danger, marginBottom: spacing.md },
  aviso: { color: colors.info, marginBottom: spacing.md },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing.sm },
  list: { marginTop: spacing.md },
  trailing: { alignItems: 'flex-end' },
  acciones: { flexDirection: 'row', marginTop: spacing.xs },
  iconBtn: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
});
```

- [ ] **Step 3: Verificación**

Run: `cd mobile && npx jest` — confirma que nada rompe.

- [ ] **Step 4: Commit**

```bash
git add mobile/api/ingredientes.js mobile/screens/InventarioScreen.js
git commit -m "feat(mobile): unidad por chips y stock inicial opcional al crear ingrediente"
```

---

### Task 4: Editar producto en MenuScreen

**Files:**
- Modify: `mobile/screens/MenuScreen.js`

**Interfaces:**
- Consumes: `updateProducto(id, payload)` de `mobile/api/productos.js` (ya existe, sin cambios).
- Produces: `MenuScreen` gana el prop `navigation` (lo necesita Task 5 para el botón "Editar receta") — se agrega en este task para no tocar la firma dos veces.

- [ ] **Step 1: Agregar modo edición**

Reemplazar el contenido completo de `mobile/screens/MenuScreen.js`:

```javascript
import React, { useCallback, useState } from 'react';
import { View, Text, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { getProductos, createProducto, updateProducto, deleteProducto } from '../api/productos';
import { getCategorias } from '../api/categorias';
import { ApiError } from '../api/client';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { Chip } from '../components/Chip';
import { ListItem } from '../components/ListItem';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

export default function MenuScreen({ navigation }) {
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [categoriaId, setCategoriaId] = useState(null);
  const [categoriaFiltro, setCategoriaFiltro] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');

  const [nombre, setNombre] = useState('');
  const [precio, setPrecio] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [disponible, setDisponible] = useState(true);
  const [editandoId, setEditandoId] = useState(null);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [prods, cats] = await Promise.all([getProductos(), getCategorias()]);
      setProductos(prods);
      setCategorias(cats);
      // updater funcional: no necesitamos categoriaId como dependencia
      setCategoriaId((actual) => (actual === null && cats.length > 0 ? cats[0].id : actual));
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

  const limpiarFormulario = () => {
    setNombre('');
    setPrecio('');
    setDescripcion('');
    setDisponible(true);
    setEditandoId(null);
  };

  const iniciarEdicion = (producto) => {
    setEditandoId(producto.id);
    setNombre(producto.nombre);
    setPrecio(String(producto.precio_venta));
    setDescripcion(producto.descripcion || '');
    setDisponible(producto.disponible);
    setCategoriaId(producto.categoria.id);
  };

  const guardarProducto = async () => {
    if (!nombre.trim() || !precio || !categoriaId) {
      setError('Completa nombre, precio y categoría');
      return;
    }

    setError('');
    try {
      if (editandoId) {
        await updateProducto(editandoId, {
          nombre: nombre.trim(),
          descripcion: descripcion.trim() || null,
          precio_venta: parseFloat(precio),
          disponible,
          id_categoria: categoriaId,
        });
      } else {
        await createProducto({
          nombre: nombre.trim(),
          descripcion: descripcion.trim(),
          precioVenta: parseFloat(precio),
          idCategoria: categoriaId,
        });
      }
      limpiarFormulario();
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el producto');
    }
  };

  const eliminar = async (id) => {
    setError('');
    setAviso('');
    try {
      // DELETE /productos/{id} responde 200 {eliminado, mensaje}: si el
      // producto tiene historial de pedidos NO se borra, se desactiva
      // (api/app/routers/productos.py). Sin mostrar `mensaje` el usuario cree
      // que borró algo que sigue ahí.
      const resultado = await deleteProducto(id);
      setAviso(resultado.mensaje);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el producto');
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  const productosVisibles = categoriaFiltro
    ? productos.filter((p) => p.categoria.id === categoriaFiltro)
    : productos;

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Gestión de Menú</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {aviso ? <Text style={styles.aviso}>{aviso}</Text> : null}

      <Text style={styles.label}>Filtrar por categoría</Text>
      <View style={styles.categorias}>
        <Chip label="Todas" selected={categoriaFiltro === null} onPress={() => setCategoriaFiltro(null)} />
        {categorias.map((cat) => (
          <Chip
            key={cat.id}
            label={cat.nombre}
            selected={categoriaFiltro === cat.id}
            onPress={() => setCategoriaFiltro(cat.id)}
          />
        ))}
      </View>

      <Text style={styles.subtitle}>{editandoId ? 'Editar producto' : 'Agregar producto'}</Text>

      <Input placeholder="Nombre" value={nombre} onChangeText={setNombre} />
      <Input placeholder="Precio" value={precio} onChangeText={setPrecio} keyboardType="numeric" />
      <Input placeholder="Descripción" value={descripcion} onChangeText={setDescripcion} />

      <View style={styles.categorias}>
        {categorias.map((cat) => (
          <Chip
            key={cat.id}
            label={cat.nombre}
            selected={categoriaId === cat.id}
            onPress={() => setCategoriaId(cat.id)}
          />
        ))}
      </View>

      {editandoId ? (
        <View style={styles.categorias}>
          <Chip label="Disponible" selected={disponible} onPress={() => setDisponible(true)} />
          <Chip label="No disponible" selected={!disponible} onPress={() => setDisponible(false)} />
        </View>
      ) : null}

      <View style={styles.formBotones}>
        <Button
          variant="secondary"
          label={editandoId ? 'Guardar cambios' : 'Agregar producto'}
          onPress={guardarProducto}
        />
        {editandoId ? (
          <Button variant="text" label="Cancelar" onPress={limpiarFormulario} />
        ) : null}
      </View>

      <FlatList
        data={productosVisibles}
        keyExtractor={(item) => item.id.toString()}
        style={styles.list}
        ListEmptyComponent={<EmptyState icon="restaurant-outline" message="Sin productos registrados." />}
        renderItem={({ item }) => (
          <ListItem
            title={item.nombre}
            subtitle={`$${item.precio_venta} · ${item.categoria.nombre}`}
            trailing={
              <View style={styles.acciones}>
                <TouchableOpacity style={styles.iconBtn} onPress={() => iniciarEdicion(item)}>
                  <Ionicons name="create-outline" size={22} color={colors.primary} />
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.iconBtn}
                  onPress={() => navigation.navigate('Receta', { productoId: item.id, productoNombre: item.nombre })}
                >
                  <Ionicons name="list-outline" size={22} color={colors.primary} />
                </TouchableOpacity>

                <TouchableOpacity style={styles.iconBtn} onPress={() => eliminar(item.id)}>
                  <Ionicons name="trash-outline" size={22} color={colors.danger} />
                </TouchableOpacity>
              </View>
            }
          />
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  label: { color: colors.textSecondary, marginBottom: spacing.xs, fontSize: typography.size.md },
  subtitle: {
    marginTop: spacing.md,
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  error: { color: colors.danger, marginBottom: spacing.md },
  aviso: { color: colors.info, marginBottom: spacing.md },
  categorias: { flexDirection: 'row', flexWrap: 'wrap' },
  formBotones: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  list: { marginTop: spacing.md },
  acciones: { flexDirection: 'row' },
  iconBtn: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
});
```

Nota: el botón "Editar receta" ya queda cableado a la ruta `Receta` en este mismo Step — Task 5 crea esa pantalla y la registra en `App.js`; hasta que Task 5 no esté hecho, ese botón navegaría a una ruta inexistente (falla en runtime, no en build/test). Si este plan se ejecuta en orden (Task 4 antes que Task 5), es un estado intermedio esperado de un solo commit a otro — no afecta tests automatizados.

- [ ] **Step 2: Verificación**

Run: `cd mobile && npx jest` — confirma que nada rompe.

- [ ] **Step 3: Commit**

```bash
git add mobile/screens/MenuScreen.js
git commit -m "feat(mobile): editar producto y filtrar menu por categoria"
```

---

### Task 5: CRUD de recetas — `api/recetas.js` + `RecetaScreen.js` + ruta

**Files:**
- Create: `mobile/api/recetas.js`
- Create: `mobile/screens/RecetaScreen.js`
- Modify: `mobile/App.js`

**Interfaces:**
- Consumes: `getIngredientes()` de `mobile/api/ingredientes.js` (ya existe). `route.params.{productoId, productoNombre}` producidos por el botón de Task 4.
- Produces: `getRecetasPorProducto`, `crearReceta`, `actualizarReceta`, `eliminarReceta`, `eliminarRecetaCompleta` en `api/recetas.js`. Ruta `Receta` en `App.js`.

Backend sin cambios — `api/app/routers/recetas.py` (`GET/POST/PUT/DELETE /producto_ingrediente`) ya está completo y probado.

- [ ] **Step 1: `mobile/api/recetas.js`**

```javascript
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

- [ ] **Step 2: `mobile/screens/RecetaScreen.js`**

```javascript
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator, Alert } from 'react-native';
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
import { Card } from '../components/Card';
import { ListItem } from '../components/ListItem';
import { Chip } from '../components/Chip';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

export default function RecetaScreen({ route }) {
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
        <ActivityIndicator size="large" color={colors.primary} />
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
        style={styles.list}
        ListEmptyComponent={<EmptyState icon="list-outline" message="Sin ingredientes en la receta aún." />}
        renderItem={({ item }) => (
          <Card style={styles.card}>
            <Text style={styles.name}>{item.ingrediente.nombre}</Text>

            {editandoId === item.id_ingrediente ? (
              <View style={styles.row}>
                <Input
                  style={{ flex: 1 }}
                  keyboardType="numeric"
                  value={cantidadEditada}
                  onChangeText={setCantidadEditada}
                />
                <Button variant="text" label="Guardar" onPress={() => guardarEdicion(item.id_ingrediente)} />
              </View>
            ) : (
              <>
                <Text style={styles.cantidad}>
                  Cantidad: {item.cantidad_requerida} {item.ingrediente.unidad}
                </Text>
                <View style={styles.row}>
                  <Button variant="text" label="Editar" onPress={() => iniciarEdicion(item)} />
                  <Button variant="text" label="Eliminar" onPress={() => eliminarLinea(item.id_ingrediente)} />
                </View>
              </>
            )}
          </Card>
        )}
      />

      <Text style={styles.subtitle}>Agregar ingrediente</Text>

      <View style={styles.chipsRow}>
        {ingredientes.map((ing) => (
          <Chip
            key={ing.id}
            label={ing.nombre}
            selected={ingredienteId === ing.id}
            onPress={() => setIngredienteId(ing.id)}
          />
        ))}
      </View>

      <Input
        placeholder="Cantidad requerida"
        value={cantidad}
        onChangeText={setCantidad}
        keyboardType="numeric"
      />

      <Button
        variant="secondary"
        label={guardando ? 'Guardando...' : 'Agregar'}
        onPress={agregarIngrediente}
        disabled={guardando}
      />

      <View style={styles.eliminarWrap}>
        <Button variant="text" label="Eliminar receta completa" onPress={confirmarEliminarTodo} />
      </View>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  subtitle: {
    marginTop: spacing.md,
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  error: { color: colors.danger, marginBottom: spacing.md },
  list: { marginBottom: spacing.md },
  card: { marginBottom: spacing.sm },
  name: { fontSize: typography.size.lg, fontWeight: typography.weight.bold, color: colors.textPrimary },
  cantidad: { color: colors.textSecondary, marginTop: spacing.xs },
  row: { flexDirection: 'row', alignItems: 'center', marginTop: spacing.sm, gap: spacing.sm },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap' },
  eliminarWrap: { marginTop: spacing.sm },
});
```

- [ ] **Step 3: Registrar la ruta en `App.js`**

Agregar el import junto a los demás screens:

```javascript
import RecetaScreen from './screens/RecetaScreen';
```

Y el `Stack.Screen`, junto al de `Menu`:

```jsx
        <Stack.Screen
          name="Receta"
          component={RecetaScreen}
        />
```

- [ ] **Step 4: Verificación**

Run: `cd mobile && npx jest` — confirma que nada rompe.

- [ ] **Step 5: Commit**

```bash
git add mobile/api/recetas.js mobile/screens/RecetaScreen.js mobile/App.js
git commit -m "feat(mobile): CRUD de recetas por producto desde MenuScreen"
```

---

### Task 6: `GET /tickets/{id}` — backend

**Files:**
- Modify: `api/app/routers/tickets.py`
- Test: `api/app/tests/test_router_tickets.py`

**Interfaces:**
- Produces: `GET /tickets/{ticket_id}` — Mesero/Cajero/Admin, mismo gate de rol que `GET /tickets` (Mesero solo si es el creador del pedido asociado), 404 si no existe, 403 si un Mesero pide un ticket ajeno. Devuelve `TicketOut`. Consumido por Task 7 (mobile).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `api/app/tests/test_router_tickets.py`:

```python
def test_obtener_ticket_por_id_mesero_propio(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    token = _token(usuario_mesero.id, RolNombre.MESERO)
    respuesta = client.get(f"/tickets/{ticket.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == ticket.id


def test_obtener_ticket_por_id_mesero_ajeno_403(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    otro_mesero = _otro_mesero(db_session, catalogos)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=otro_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=otro_mesero.id)

    token = _token(usuario_mesero.id, RolNombre.MESERO)
    respuesta = client.get(f"/tickets/{ticket.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 403


def test_obtener_ticket_por_id_inexistente_404(client, db_session, catalogos, usuario_mesero):
    token = _token(usuario_mesero.id, RolNombre.MESERO)
    respuesta = client.get("/tickets/99999", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 404


def test_obtener_ticket_por_id_cajero_ve_cualquiera(client, db_session, catalogos, mesa_libre, usuario_mesero):
    producto = _crear_producto(db_session)
    pedido = crear_pedido(db_session, PedidoCreate(mesa_id=mesa_libre.id, usuario_id=usuario_mesero.id, items=[DetallePedidoCreate(id_producto=producto.id, cantidad=1)]))
    cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.EN_PREPARACION)
    pedido, _ = cambiar_estado_pedido(db_session, pedido, EstatusPedidoNombre.LISTO)
    ticket = cerrar_cuenta(db_session, pedido, usuario_id=usuario_mesero.id)

    token = _token(999, RolNombre.CAJERO)
    respuesta = client.get(f"/tickets/{ticket.id}", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
```

Los imports/fixtures (`_crear_producto`, `_otro_mesero`, `_token`, `crear_pedido`, `cambiar_estado_pedido`, `cerrar_cuenta`, `PedidoCreate`, `DetallePedidoCreate`, `EstatusPedidoNombre`, `RolNombre`) ya están en el archivo (usados por los tests de `GET /tickets` existentes).

- [ ] **Step 2: Correr los tests, verificar que fallan**

Run: `cd api && python -m pytest app/tests/test_router_tickets.py -v`
Expected: FAIL con 404 (la ruta `/tickets/{id}` no existe todavía — nota: el 404 esperado del test `test_obtener_ticket_por_id_inexistente_404` pasaría "por accidente" con la ruta ausente; los otros 3 tests SÍ fallan de verdad).

- [ ] **Step 3: Implementar**

Agregar a `api/app/routers/tickets.py`, tras el import de `fastapi`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
```

Y el nuevo endpoint, tras `listar`:

```python
@router.get("/{ticket_id}", response_model=TicketOut)
def obtener(
    ticket_id: int,
    db: Session = Depends(get_db),
    usuario: TokenData = Depends(
        require_rol(RolNombre.MESERO, RolNombre.CAJERO, RolNombre.ADMINISTRADOR)
    ),
) -> Ticket:
    ticket = db.query(Ticket).options(*_TICKET_LOAD_OPTIONS).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado")

    if usuario.rol == RolNombre.MESERO and ticket.pedido.id_usuario != usuario.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver este ticket"
        )

    return ticket
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && python -m pytest app/tests/test_router_tickets.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Correr la suite completa del backend**

Run: `cd api && python -m pytest -v`
Expected: PASS (todos)

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/tickets.py api/app/tests/test_router_tickets.py
git commit -m "feat(api): endpoint GET /tickets/{id} para consultar un ticket individual"
```

---

### Task 7: PagoScreen muestra el total real antes de cobrar

**Files:**
- Modify: `mobile/api/tickets.js`
- Modify: `mobile/screens/PagoScreen.js`

**Interfaces:**
- Consumes: `GET /tickets/{id}` de Task 6.
- Produces: `getTicket(ticketId)` en `api/tickets.js`.

- [ ] **Step 1: `api/tickets.js` — agregar `getTicket`**

```javascript
import { request } from './client';

export function getTickets({ pagado } = {}) {
  const query = pagado === undefined ? '' : `?pagado=${pagado}`;
  return request(`/tickets${query}`);
}

export function getTicket(ticketId) {
  return request(`/tickets/${ticketId}`);
}
```

- [ ] **Step 2: `PagoScreen.js` — traer y mostrar el ticket**

Reemplazar el contenido completo de `mobile/screens/PagoScreen.js`:

```javascript
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido } from '../api/pedidos_caja';
import { getTicket } from '../api/tickets';
import { registrarVenta } from '../api/caja';
import { ApiError } from '../api/client';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Chip } from '../components/Chip';
import { Input } from '../components/Input';
import { colors, typography, spacing, radii } from '../theme';

const METODOS = [
  { key: 'Efectivo', label: 'Efectivo' },
  { key: 'Tarjeta débito', label: 'Tarjeta débito' },
  { key: 'Tarjeta crédito', label: 'Tarjeta crédito' },
  { key: 'Transferencia', label: 'Transferencia' },
];

export default function PagoScreen({ route, navigation }) {
  const { ticketId, pedidoId, numeroMesa } = route.params;

  const [pedido, setPedido] = useState(null);
  const [ticket, setTicket] = useState(null);
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
      const [pedidoData, ticketData] = await Promise.all([getPedido(pedidoId), getTicket(ticketId)]);
      setPedido(pedidoData);
      setTicket(ticketData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar el pedido');
    } finally {
      setLoading(false);
    }
  }, [pedidoId, ticketId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

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
      const ticketPagado = await registrarVenta({ ticketId, metodoPago, monto: Number(monto) });
      setResultado(ticketPagado);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo procesar el pago');
    } finally {
      setProcesando(false);
    }
  };

  if (loading && !pedido) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (error && !pedido) {
    return (
      <View style={styles.center}>
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
        <Button variant="primary" label="Reintentar" onPress={cargar} />
      </View>
    );
  }

  if (resultado) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>Pago registrado</Text>
        <Text style={styles.text}>Total: ${resultado.total}</Text>
        <Text style={styles.text}>Cambio: ${resultado.pago.cambio}</Text>
        <Button variant="primary" label="Volver a Caja" onPress={() => navigation.navigate('Caja')} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: spacing.xxl }}>

      <Text style={styles.title}>Procesar Pago</Text>

      <Card>
        <Text style={styles.subtitle}>Mesa {numeroMesa ?? pedido.id_mesa} — Pedido #{pedido.id}</Text>

        {pedido.detalle.map((item) => (
          <Text key={item.id} style={styles.text}>
            {item.producto.nombre} x{item.cantidad} — ${item.precio_unitario}
          </Text>
        ))}

        {ticket ? (
          <>
            <Text style={styles.totalLine}>Subtotal: ${ticket.subtotal}</Text>
            <Text style={styles.totalLine}>IVA: ${ticket.iva}</Text>
            <Text style={styles.total}>Total a cobrar: ${ticket.total}</Text>
          </>
        ) : null}
      </Card>

      <Text style={styles.subtitle}>Método de pago</Text>

      <View style={styles.row}>
        {METODOS.map((m) => (
          <Chip
            key={m.key}
            label={m.label}
            selected={metodoPago === m.key}
            onPress={() => !procesando && setMetodoPago(m.key)}
          />
        ))}
      </View>

      <Input
        label="Monto recibido"
        keyboardType="numeric"
        placeholder="Ej. 200"
        value={monto}
        onChangeText={setMonto}
        editable={!procesando}
      />

      {error ? (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <Button
        variant="primary"
        label="Confirmar y Pagar"
        onPress={pagar}
        loading={procesando}
        disabled={procesando}
      />

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.xl },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  subtitle: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  text: { fontSize: typography.size.lg, color: colors.textPrimary },
  totalLine: { fontSize: typography.size.md, color: colors.textSecondary, marginTop: spacing.xs },
  total: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginTop: spacing.sm,
  },
  errorBanner: {
    backgroundColor: colors.dangerTint,
    borderWidth: 1,
    borderColor: 'rgba(192,57,43,0.3)',
    borderRadius: radii.r8,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  errorText: { color: colors.danger, fontSize: typography.size.md },
  row: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing.md },
});
```

- [ ] **Step 3: Verificación**

Run: `cd mobile && npx jest` — confirma que nada rompe.

- [ ] **Step 4: Commit**

```bash
git add mobile/api/tickets.js mobile/screens/PagoScreen.js
git commit -m "feat(mobile): PagoScreen muestra subtotal, iva y total reales antes de cobrar"
```

---

### Task 8: Fix de rango de fechas en reportes financieros

**Files:**
- Modify: `api/app/routers/reportes.py`
- Test: `api/app/tests/test_router_reportes.py`

**Interfaces:**
- Produces: `_rango_por_defecto` normaliza `hasta` a fin de día cuando llega sin componente de hora. Afecta a los 9 endpoints que la llaman (mismo punto de cambio).

- [ ] **Step 1: Escribir el test que falla**

Agregar a `api/app/tests/test_router_reportes.py`:

```python
def test_financiero_json_hasta_sin_hora_incluye_ventas_del_dia(client, catalogos, venta_de_junio):
    """Regresión del hallazgo real: hasta=2026-06-15 (sin hora) se interpretaba
    como medianoche 00:00:00, excluyendo silenciosamente las ventas de ese
    mismo día (venta_de_junio ocurre justo en esa fecha)."""
    token = _token(catalogos, RolNombre.ADMINISTRADOR)

    respuesta = client.get(
        "/api/reportes/financiero?desde=2026-06-01&hasta=2026-06-15",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["total_ventas"] == "638.00"
```

- [ ] **Step 2: Correr el test, verificar que falla**

Run: `cd api && python -m pytest app/tests/test_router_reportes.py::test_financiero_json_hasta_sin_hora_incluye_ventas_del_dia -v`
Expected: FAIL — `total_ventas` viene en `"0.00"` o `0` (la venta de las 00:00:00 exactas del 15 de junio queda excluida por el filtro `<= hasta` cuando `hasta` es también medianoche del 15... en realidad el fixture `venta_de_junio` usa `datetime(2026, 6, 15, tzinfo=timezone.utc)` que también es medianoche exacta, así que con la implementación actual el `<=` sí la incluye por coincidencia de horario exacto. Para que el test exponga el bug real hay que mover el fixture un poco: ver nota abajo.

**Nota importante:** el fixture `venta_de_junio` (línea 54 de `test_router_reportes.py`) usa `fecha = datetime(2026, 6, 15, tzinfo=timezone.utc)`, que es exactamente medianoche — igual que el `hasta` sin normalizar. Para que el test realmente distinga "incluye correctamente" de "excluye por accidente de que ambos son medianoche", cambiar la fecha del ticket a una hora avanzada del mismo día en el test nuevo. Como `venta_de_junio` es una fixture compartida por otros tests que sí esperan medianoche exacta, no modificarla — en su lugar, este test nuevo no debe depender de esa fixture tal cual. Usar en cambio esta variante local dentro del mismo test, sin fixture compartida:

```python
def test_financiero_json_hasta_sin_hora_incluye_ventas_del_dia(
    client, db_session, catalogos, mesa_libre, usuario_mesero, producto_con_receta
):
    """Regresión del hallazgo real: hasta=2026-06-15 (sin hora) se interpretaba
    como medianoche 00:00:00, excluyendo silenciosamente las ventas ocurridas
    más tarde ese mismo día."""
    producto, _ = producto_con_receta
    fecha_tarde = datetime(2026, 6, 15, 18, 30, tzinfo=timezone.utc)
    pedido = Pedido(
        fecha=fecha_tarde,
        id_mesa=mesa_libre.id,
        id_usuario=usuario_mesero.id,
        id_estatus=catalogos["estatus_pedidos"][EstatusPedidoNombre.ENTREGADO].id,
    )
    db_session.add(pedido)
    db_session.flush()
    detalle = DetallePedido(
        cantidad=10,
        precio_unitario=Decimal("55.00"),
        id_producto=producto.id,
        id_pedido=pedido.id,
        id_estatus=catalogos["estatus_cocina"][EstatusCocinaNombre.LISTO].id,
    )
    db_session.add(detalle)
    db_session.flush()
    ticket = Ticket(
        subtotal=Decimal("550.00"), iva=Decimal("88.00"), total=Decimal("638.00"),
        fecha_emision=fecha_tarde, id_pedido=pedido.id, id_usuario=usuario_mesero.id,
    )
    db_session.add(ticket)
    db_session.flush()
    pago = Pago(
        monto_recibido=ticket.total, cambio=Decimal("0.00"),
        id_ticket=ticket.id, id_metodo=catalogos["metodos_pago"]["Efectivo"].id,
    )
    db_session.add(pago)
    db_session.flush()

    token = _token(catalogos, RolNombre.ADMINISTRADOR)
    respuesta = client.get(
        "/api/reportes/financiero?desde=2026-06-01&hasta=2026-06-15",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["total_ventas"] == "638.00"
```

Este SÍ falla contra la implementación actual, porque `hasta=2026-06-15` parsea a `2026-06-15T00:00:00`, y la venta de las 18:30 queda fuera del filtro `Ticket.fecha_emision <= hasta`.

Run: `cd api && python -m pytest app/tests/test_router_reportes.py::test_financiero_json_hasta_sin_hora_incluye_ventas_del_dia -v`
Expected: FAIL

- [ ] **Step 3: Implementar el fix**

En `api/app/routers/reportes.py`, modificar `_rango_por_defecto`:

```python
def _rango_por_defecto(desde: datetime | None, hasta: datetime | None) -> tuple[datetime, datetime]:
    hasta = hasta or datetime.now(timezone.utc)
    if hasta.time() == datetime.min.time():
        # `hasta` llegó como fecha pelada (ej. "2026-08-08"), que FastAPI
        # parsea a medianoche — sin este ajuste, las ventas del propio día
        # `hasta` quedan excluidas silenciosamente del reporte.
        hasta = hasta.replace(hour=23, minute=59, second=59, microsecond=999999)
    desde = desde or (hasta - timedelta(days=30))
    return desde, hasta
```

- [ ] **Step 4: Correr los tests, verificar que pasan**

Run: `cd api && python -m pytest app/tests/test_router_reportes.py -v`
Expected: PASS (todos, incluyendo `test_financiero_json_devuelve_ranking_y_margen` que ya mandaba `hasta` con hora explícita — no debe verse afectado)

- [ ] **Step 5: Correr la suite completa del backend**

Run: `cd api && python -m pytest -v`
Expected: PASS (todos)

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/reportes.py api/app/tests/test_router_reportes.py
git commit -m "fix(api): hasta sin hora en reportes financieros ya no excluye ventas del mismo dia"
```

---

### Task 9: Cálculo automático de monto en "Comprar insumo"

**Files:**
- Modify: `mobile/screens/GastosScreen.js`

**Interfaces:** Ninguna nueva — usa `crearCompra` de `mobile/api/compras.js` (ya existe, sin cambios de contrato).

- [ ] **Step 1: Quitar el input de monto, calcularlo en vivo**

En `mobile/screens/GastosScreen.js`, reemplazar el bloque de estado y las funciones relacionadas a "Comprar insumo":

Cambiar:
```javascript
  const [montoCompra, setMontoCompra] = useState('');
```
por (se elimina esa línea — ya no hay estado de monto manual).

Cambiar la función `registrarCompra`:

```javascript
  const registrarCompra = async () => {
    if (!ingredienteId || !cantidadCompra) {
      setErrorCompra('Selecciona un ingrediente y completa la cantidad');
      return;
    }

    setComprando(true);
    setErrorCompra('');
    setResultadoCompra(null);
    try {
      const ingrediente = ingredientes.find((i) => i.id === ingredienteId);
      const monto = parseFloat(cantidadCompra) * Number(ingrediente.costo_unitario);
      const resultado = await crearCompra({
        ingredienteId,
        cantidad: parseFloat(cantidadCompra),
        monto,
      });
      setResultadoCompra(resultado);
      setCantidadCompra('');
      await cargarResumen();
    } catch (err) {
      setErrorCompra(err instanceof ApiError ? err.message : 'No se pudo registrar la compra');
    } finally {
      setComprando(false);
    }
  };
```

Y en `renderHeader`, dentro de la card "Comprar insumo", reemplazar el `Input` de "Monto" por un texto de solo lectura calculado en vivo, ubicado justo después del `Input` de "Cantidad":

```jsx
        <Input
          placeholder="Cantidad"
          value={cantidadCompra}
          onChangeText={setCantidadCompra}
          keyboardType="numeric"
        />

        {ingredienteId && cantidadCompra ? (
          <Text style={styles.montoCalculado}>
            Monto: $
            {(
              parseFloat(cantidadCompra) *
              Number(ingredientes.find((i) => i.id === ingredienteId)?.costo_unitario || 0)
            ).toFixed(2)}
          </Text>
        ) : null}
```

(esto reemplaza el bloque `<Input placeholder="Monto" value={montoCompra} onChangeText={setMontoCompra} keyboardType="numeric" />` que existía antes).

Agregar el estilo `montoCalculado` al `StyleSheet.create` del archivo, junto a `successText`:

```javascript
  montoCalculado: { color: colors.textPrimary, fontWeight: typography.weight.semibold, marginBottom: spacing.md },
```

- [ ] **Step 2: Verificación**

Run: `cd mobile && npx jest` — confirma que nada rompe.

- [ ] **Step 3: Commit**

```bash
git add mobile/screens/GastosScreen.js
git commit -m "feat(mobile): calcular automaticamente el monto al comprar insumo"
```

---

## Self-Review

**Cobertura del spec:**
- #1 → Task 1. #5 → Task 2. #6 → Task 3. #7 → Task 4. #8 → Task 5. #9 → Tasks 6+7. #10 → Task 8. #13 → Task 9. #14 → Task 4 (incluido junto con #7 por tocar el mismo archivo/misma sección de categorías). ✓ Los 9 hallazgos accionables cubiertos.

**Placeholder scan:** sin TBD/TODO. La nota de Task 4 sobre el estado intermedio de la ruta `Receta` está documentada explícitamente, no es un placeholder oculto.

**Type consistency:** `getTicket(ticketId)` (Task 7) coincide con `GET /tickets/{ticket_id}` (Task 6). `createIngrediente({..., stockInicial})` (Task 3) consistente entre `api/ingredientes.js` y su único caller en `InventarioScreen.js`. `navigation` prop de `MenuScreen` (Task 4) es lo que Task 5 asume ya disponible para el botón "Editar receta" — mismo nombre de ruta `Receta` en ambos.

---

**Plan completo y guardado en `docs/superpowers/plans/2026-08-08-hallazgos-restantes.md`.**
