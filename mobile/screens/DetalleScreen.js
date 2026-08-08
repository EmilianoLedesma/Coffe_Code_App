import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ScrollView } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido, cambiarEstadoPedido } from '../api/pedidos';
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

  const puedeEntregar =
    (rol === 'Mesero' || rol === 'Administrador') && pedido.estatus.nombre === 'Listo';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

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
          trailing={<Badge label={item.estatus.nombre} tone="neutral" />}
        />
      ))}

      {pedido.total !== null && (
        <Text style={styles.total}>Total: ${pedido.total}</Text>
      )}

      {error ? <Text style={styles.error}>{error}</Text> : null}

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

    </ScrollView>
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
  error: { color: colors.danger, marginBottom: spacing.lg, textAlign: 'center' },
  total: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginTop: spacing.md,
    marginBottom: spacing.xl,
  },
  entregarWrap: { marginBottom: spacing.sm },
});
