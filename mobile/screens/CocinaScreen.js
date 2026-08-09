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
