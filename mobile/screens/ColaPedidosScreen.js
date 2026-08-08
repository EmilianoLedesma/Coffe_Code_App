import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getColaPendientes } from '../api/pedidos_cocina';
import { getMesas } from '../api/mesas';
import { ApiError } from '../api/client';
import { connectToChannel } from '../ws/client';
import { ListItem } from '../components/ListItem';
import { Badge } from '../components/Badge';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

const TONE_POR_ESTATUS = {
  Pendiente: 'warning',
  'En preparación': 'info',
  Listo: 'success',
};

export default function ColaPedidosScreen({ navigation }) {
  const [pedidos, setPedidos] = useState([]);
  const [numeroPorMesa, setNumeroPorMesa] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [lista, mesas] = await Promise.all([getColaPendientes(), getMesas()]);
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

  useFocusEffect(
    useCallback(() => {
      let cerrar = null;
      let cancelado = false;

      connectToChannel('cocina', {
        onMessage: (evento) => {
          if (evento.evento === 'nuevo_pedido') {
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
    }, [cargar])
  );

  if (loading && pedidos.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
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
        ListEmptyComponent={
          <EmptyState
            icon="checkmark-done-outline"
            message="Sin pedidos pendientes. Aparecerán aquí en cuanto un mesero cree uno."
          />
        }
        renderItem={({ item }) => (
          <ListItem
            title={`Mesa ${numeroPorMesa[item.id_mesa] ?? item.id_mesa}`}
            subtitle={`Items: ${item.detalle.length}`}
            trailing={<Badge label={item.estatus.nombre} tone={TONE_POR_ESTATUS[item.estatus.nombre] || 'neutral'} />}
            onPress={() =>
              navigation.navigate('CocinaDetalle', {
                pedidoId: item.id,
                numeroMesa: numeroPorMesa[item.id_mesa],
              })
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
  error: { color: colors.danger, marginBottom: spacing.md },
});
