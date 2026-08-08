import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getColaPendientes } from '../api/pedidos_cocina';
import { Card } from '../components/Card';
import { ListItem } from '../components/ListItem';
import { colors, typography, spacing } from '../theme';

export default function CocinaScreen({ navigation }) {
  const [pendientes, setPendientes] = useState(0);

  useFocusEffect(
    useCallback(() => {
      getColaPendientes()
        .then((data) => setPendientes(data.length))
        .catch(() => setPendientes(0));
    }, [])
  );

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Cocina</Text>
      <Text style={styles.subtitle}>Gestión operativa de pedidos</Text>

      <Card size="hero" style={styles.heroCard}>
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
