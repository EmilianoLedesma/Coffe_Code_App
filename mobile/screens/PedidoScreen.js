import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { getProductos } from '../api/productos';
import { crearPedido } from '../api/pedidos';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Card } from '../components/Card';
import { ListItem } from '../components/ListItem';
import { Button } from '../components/Button';
import { colors, typography, spacing } from '../theme';

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
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Mesa {numeroMesa ?? mesaId}</Text>

      <Text style={styles.subtitle}>Pedido actual</Text>
      <Card style={styles.carritoCard}>
        {pedido.length === 0 ? (
          <Text style={styles.vacio}>Sin productos aún</Text>
        ) : (
          pedido.map((item) => (
            <Text key={item.id_producto} style={styles.carritoItem}>{item.nombre} x{item.cantidad}</Text>
          ))
        )}
      </Card>

      <Text style={styles.subtitle}>Menú</Text>

      <FlatList
        data={menu}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <ListItem
            title={item.nombre}
            subtitle={`$${item.precio_venta}`}
            trailing={<Text style={styles.agregar}>+</Text>}
            onPress={() => agregarProducto(item)}
          />
        )}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Button
        variant="primary"
        label={guardando ? 'Guardando...' : '✔ Guardar / Finalizar pedido'}
        onPress={guardarPedido}
        disabled={guardando}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: spacing.xl },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  subtitle: {
    marginTop: spacing.lg,
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  carritoCard: { marginBottom: spacing.sm },
  vacio: { color: colors.textSecondary },
  carritoItem: { color: colors.textPrimary, fontSize: typography.size.md },
  agregar: { fontWeight: typography.weight.bold, color: colors.primary, fontSize: typography.size.xl },
  error: { color: colors.danger, marginTop: spacing.md, textAlign: 'center' },
});
