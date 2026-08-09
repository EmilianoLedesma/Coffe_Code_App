import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedidosActivosDeMesa } from '../api/pedidos';
import { ApiError } from '../api/client';
import { connectToChannel } from '../ws/client';
import { ListItem } from '../components/ListItem';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';
import { TONE_POR_ESTATUS_PEDIDO } from '../constants/estatusPedido';

export default function PedidosMesaScreen({ route, navigation }) {
  const { mesaId, numeroMesa } = route.params;
  const [pedidos, setPedidos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPedidos(await getPedidosActivosDeMesa(mesaId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, [mesaId]);

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
          if (evento.mesa_id !== mesaId) return;

          if (evento.evento === 'pedido_pagado' && evento.mesa_liberada) {
            navigation.navigate('Mesas');
            return;
          }

          if (
            evento.evento === 'pedido_activado' ||
            evento.evento === 'pedido_listo' ||
            evento.evento === 'pedido_pagado'
          ) {
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
    }, [mesaId, cargar])
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Mesa {numeroMesa}</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={pedidos}
        keyExtractor={(item) => item.id.toString()}
        ListEmptyComponent={
          <EmptyState icon="receipt-outline" message="Sin pedidos activos en esta mesa." />
        }
        renderItem={({ item }) => (
          <ListItem
            title={`Pedido #${item.id}`}
            subtitle={`${item.detalle.length} ítem(s)`}
            trailing={
              <Badge
                label={item.estatus.nombre}
                tone={TONE_POR_ESTATUS_PEDIDO[item.estatus.nombre] || 'neutral'}
              />
            }
            onPress={() => navigation.navigate('Detalle', { pedidoId: item.id, numeroMesa })}
          />
        )}
      />

      <Button
        variant="primary"
        label="Nuevo pedido"
        onPress={() => navigation.navigate('Pedido', { mesaId, numeroMesa })}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
    textAlign: 'center',
  },
  error: { color: colors.danger, textAlign: 'center', marginBottom: spacing.md },
});
