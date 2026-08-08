import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ScrollView, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido, cambiarEstadoPedido } from '../api/pedidos_cocina';
import { ApiError } from '../api/client';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { ListItem } from '../components/ListItem';
import { colors, typography, spacing } from '../theme';

const SIGUIENTE_ESTATUS = {
  Pendiente: 'En preparación',
  'En preparación': 'Listo',
};

export default function CocinaDetalleScreen({ route, navigation }) {
  const { pedidoId, numeroMesa } = route.params;
  const [pedido, setPedido] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cambiando, setCambiando] = useState(false);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPedido(await getPedido(pedidoId));
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

  const avanzarEstado = async () => {
    const siguiente = SIGUIENTE_ESTATUS[pedido.estatus.nombre];
    if (!siguiente) return;

    setCambiando(true);
    setError('');
    try {
      const actualizado = await cambiarEstadoPedido(pedidoId, siguiente);
      setPedido(actualizado);

      if (siguiente !== 'Listo') return;

      const alertas = actualizado.alertas_stock_bajo || [];

      if (alertas.length > 0) {
        Alert.alert(
          'Stock bajo',
          `Estos ingredientes quedaron bajo el mínimo: ${alertas.join(', ')}`,
          [{ text: 'Entendido', onPress: () => navigation.goBack() }]
        );
      } else {
        navigation.goBack();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cambiar el estatus');
    } finally {
      setCambiando(false);
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

  const siguiente = SIGUIENTE_ESTATUS[pedido.estatus.nombre];

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: spacing.xl }}>

      <Card style={styles.header}>
        <Text style={styles.title}>Pedido #{pedido.id} — Mesa {numeroMesa ?? pedido.id_mesa}</Text>
        <Text style={styles.estado}>Estado: {pedido.estatus.nombre}</Text>
      </Card>

      {pedido.detalle.map((item) => (
        <ListItem
          key={item.id}
          title={`${item.producto.nombre} x${item.cantidad}`}
          subtitle={item.especificaciones || undefined}
        />
      ))}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {siguiente ? (
        <Button
          variant="primary"
          label={cambiando ? 'Actualizando...' : `Marcar como ${siguiente}`}
          onPress={avanzarEstado}
          disabled={cambiando}
        />
      ) : (
        <Text style={styles.sinTransiciones}>No hay más transiciones desde cocina</Text>
      )}

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { marginBottom: spacing.lg },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  estado: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.bold,
    color: colors.secondary,
  },
  error: { color: colors.danger, marginBottom: spacing.lg, textAlign: 'center' },
  sinTransiciones: { color: colors.textSecondary, textAlign: 'center' },
});
