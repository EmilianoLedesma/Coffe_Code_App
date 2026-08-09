import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getTickets } from '../api/tickets';
import { getMesas } from '../api/mesas';
import { ApiError } from '../api/client';
import { connectToChannel } from '../ws/client';
import { Button } from '../components/Button';
import { ListItem } from '../components/ListItem';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

export default function CajaScreen({ navigation }) {
  const [tickets, setTickets] = useState([]);
  const [numeroPorMesa, setNumeroPorMesa] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [lista, mesas] = await Promise.all([getTickets({ pagado: false }), getMesas()]);
      setTickets(lista);
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

      connectToChannel('caja', {
        onMessage: (evento) => {
          if (evento.evento === 'pedido_activado') {
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
    }, [cargar])
  );

  if (loading && tickets.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Caja</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={tickets}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingBottom: spacing.xxl }}
        ListEmptyComponent={
          <EmptyState
            icon="cash-outline"
            message="Sin cuentas por cobrar. Aparecerán aquí cuando el Mesero cierre la cuenta de un pedido Listo."
          />
        }
        renderItem={({ item }) => (
          <ListItem
            title={`Mesa ${numeroPorMesa[item.id_mesa] ?? item.id_mesa}`}
            subtitle={`Ticket #${item.id} — Total $${item.total}`}
            trailing={
              <Button
                variant="primary"
                label="Cobrar"
                onPress={() =>
                  navigation.navigate('Pago', {
                    ticketId: item.id,
                    numeroMesa: numeroPorMesa[item.id_mesa],
                  })
                }
              />
            }
          />
        )}
        ListFooterComponent={() => (
          <View>
            <Button
              variant="secondary"
              label="Gastos y cuentas"
              onPress={() => navigation.navigate('Gastos')}
            />
          </View>
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
