import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, FlatList } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import {
  getPedido,
  cambiarEstadoPedido,
  agregarItemPedido,
  actualizarItemPedido,
  eliminarItemPedido,
  cerrarCuenta,
} from '../api/pedidos';
import { getProductos } from '../api/productos';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { connectToChannel } from '../ws/client';
import { Card } from '../components/Card';
import { ListItem } from '../components/ListItem';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { colors, typography, spacing } from '../theme';
import { TONE_POR_ESTATUS_PEDIDO } from '../constants/estatusPedido';

export default function DetalleScreen({ route }) {
  const { pedidoId, numeroMesa } = route.params;
  const { rol } = useAuth();
  const [pedido, setPedido] = useState(null);
  const [menu, setMenu] = useState([]);
  const [loading, setLoading] = useState(true);
  const [entregando, setEntregando] = useState(false);
  const [cerrandoCuenta, setCerrandoCuenta] = useState(false);
  const [editandoItemId, setEditandoItemId] = useState(null);
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

  useFocusEffect(
    useCallback(() => {
      let cancelado = false;
      (async () => {
        try {
          const productos = await getProductos();
          if (!cancelado) setMenu(productos.filter((p) => p.disponible !== false));
        } catch (err) {
          // el menú es solo para agregar items; si falla, se oculta esa sección
        }
      })();
      return () => {
        cancelado = true;
      };
    }, [])
  );

  useFocusEffect(
    useCallback(() => {
      let cerrar = null;
      let cancelado = false;

      connectToChannel('mesero', {
        onMessage: (evento) => {
          if (evento.evento === 'pedido_listo' && evento.pedido_id === pedidoId) {
            cargar();
          }
        },
        onClose: cargar,
      }).then((unsub) => {
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
    }, [pedidoId, cargar])
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

  const handleCerrarCuenta = async () => {
    setCerrandoCuenta(true);
    setError('');
    try {
      await cerrarCuenta(pedidoId);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cerrar la cuenta');
    } finally {
      setCerrandoCuenta(false);
    }
  };

  const cambiarCantidad = async (itemId, nuevaCantidad) => {
    if (nuevaCantidad < 1) return;
    setEditandoItemId(itemId);
    setError('');
    try {
      setPedido(await actualizarItemPedido(pedidoId, itemId, { cantidad: nuevaCantidad }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo actualizar el ítem');
    } finally {
      setEditandoItemId(null);
    }
  };

  const quitarItem = async (itemId) => {
    setEditandoItemId(itemId);
    setError('');
    try {
      setPedido(await eliminarItemPedido(pedidoId, itemId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo quitar el ítem');
    } finally {
      setEditandoItemId(null);
    }
  };

  const agregarProducto = async (producto) => {
    setError('');
    try {
      setPedido(await agregarItemPedido(pedidoId, { idProducto: producto.id, cantidad: 1 }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo agregar el producto');
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
        <Text style={styles.error}>{error}</Text>
        <Button variant="primary" label="Reintentar" onPress={cargar} />
      </View>
    );
  }

  const esMeseroOAdmin = rol === 'Mesero' || rol === 'Administrador';
  const esPendiente = pedido.estatus.nombre === 'Pendiente';
  const esListo = pedido.estatus.nombre === 'Listo';
  const puedeEditar = esMeseroOAdmin && esPendiente;
  const puedeCerrarCuenta = esMeseroOAdmin && esListo;
  const puedeEntregar = esMeseroOAdmin && esListo;

  const cabecera = (
    <>
      <Card style={styles.infoCard}>
        <Text style={styles.title}>Pedido #{pedido.id} — Mesa {numeroMesa ?? pedido.id_mesa}</Text>
        <Badge
          label={pedido.estatus.nombre}
          tone={TONE_POR_ESTATUS_PEDIDO[pedido.estatus.nombre] || 'neutral'}
        />
      </Card>

      {pedido.detalle.map((item) => (
        <ListItem
          key={item.id}
          title={`${item.producto.nombre} x${item.cantidad}`}
          subtitle={`$${item.precio_unitario} c/u`}
          trailing={
            puedeEditar ? (
              <View style={styles.editRow}>
                <Button
                  variant="text"
                  label="-"
                  onPress={() => cambiarCantidad(item.id, item.cantidad - 1)}
                  disabled={editandoItemId === item.id}
                />
                <Button
                  variant="text"
                  label="+"
                  onPress={() => cambiarCantidad(item.id, item.cantidad + 1)}
                  disabled={editandoItemId === item.id}
                />
                <Button
                  variant="text"
                  label="Quitar"
                  onPress={() => quitarItem(item.id)}
                  disabled={editandoItemId === item.id}
                />
              </View>
            ) : (
              <Badge label={item.estatus.nombre} tone="neutral" />
            )
          }
        />
      ))}

      {puedeEditar && <Text style={styles.subtitle}>Agregar producto</Text>}

      {pedido.total !== null && (
        <Text style={styles.total}>Total: ${pedido.total}</Text>
      )}
    </>
  );

  const pie = (
    <>
      {error ? <Text style={styles.error}>{error}</Text> : null}

      {puedeCerrarCuenta && (
        <View style={styles.entregarWrap}>
          <Button
            variant="secondary"
            label={cerrandoCuenta ? 'Cerrando...' : 'Cerrar cuenta'}
            onPress={handleCerrarCuenta}
            disabled={cerrandoCuenta}
          />
        </View>
      )}

      {puedeEntregar && (
        <View style={styles.entregarWrap}>
          <Button
            variant="primary"
            label={entregando ? 'Actualizando...' : 'Marcar como Entregado'}
            onPress={marcarEntregado}
            disabled={entregando}
          />
        </View>
      )}

      <Button variant="text" label="Actualizar" onPress={cargar} />
    </>
  );

  return (
    <FlatList
      style={styles.container}
      contentContainerStyle={styles.content}
      data={puedeEditar ? menu : []}
      keyExtractor={(item) => item.id.toString()}
      renderItem={({ item }) => (
        <ListItem
          title={item.nombre}
          subtitle={`$${item.precio_venta}`}
          trailing={<Text style={styles.agregar}>+</Text>}
          onPress={() => agregarProducto(item)}
        />
      )}
      ListHeaderComponent={cabecera}
      ListFooterComponent={pie}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.xl },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.xl, gap: spacing.lg },
  infoCard: { marginBottom: spacing.lg, gap: spacing.sm },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
  },
  subtitle: {
    marginTop: spacing.lg,
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  error: { color: colors.danger, marginBottom: spacing.lg, textAlign: 'center' },
  total: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginTop: spacing.md,
    marginBottom: spacing.xl,
  },
  entregarWrap: { marginBottom: spacing.sm },
  editRow: { flexDirection: 'row', gap: spacing.sm },
  agregar: { fontWeight: typography.weight.bold, color: colors.primary, fontSize: typography.size.xl },
});
