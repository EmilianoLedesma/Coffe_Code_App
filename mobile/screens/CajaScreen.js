import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedidosListos } from '../api/pedidos_caja';
import { getMesas } from '../api/mesas';
import { ApiError } from '../api/client';
import { connectToChannel } from '../ws/client';
import { Button } from '../components/Button';
import { ListItem } from '../components/ListItem';
import { Badge } from '../components/Badge';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

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

      <Text style={styles.title}>Caja</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={pedidos}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingBottom: spacing.xxl }}
        ListEmptyComponent={
          <EmptyState
            icon="cash-outline"
            message="Sin pedidos por cobrar. Aparecerán aquí cuando cocina marque un pedido como Listo."
          />
        }
        renderItem={({ item }) => {
          // registrar_venta pone `total` pero deja el estatus en `Listo`
          // (api/app/services/ventas.py:63): el pedido sigue en esta cola
          // hasta que el Mesero lo marque Entregado. Ofrecerle "Cobrar" otra
          // vez garantiza un 409 de pago duplicado.
          const pagado = item.total !== null;
          return (
            <ListItem
              title={`Mesa ${numeroPorMesa[item.id_mesa] ?? item.id_mesa}`}
              subtitle={`Pedido #${item.id} — ${item.detalle.length} ítem(s)`}
              trailing={
                pagado ? (
                  <Badge label="Cobrado" tone="info" />
                ) : (
                  <Button
                    variant="primary"
                    label="Cobrar"
                    onPress={() =>
                      navigation.navigate('Pago', {
                        pedidoId: item.id,
                        numeroMesa: numeroPorMesa[item.id_mesa],
                      })
                    }
                  />
                )
              }
            />
          );
        }}
        ListFooterComponent={() => (
          <View>
            <Button
              variant="secondary"
              label="Gastos y cuentas"
              onPress={() => navigation.navigate('Gastos')}
            />
            {/* Task 4 agrega aquí el botón "Registrar compra de insumo",
                junto con la ruta `Compras` que necesita para no crashear. */}
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
