import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getMesas } from '../api/mesas';
import { getPedidoActivoDeMesa } from '../api/pedidos';
import { ApiError } from '../api/client';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { colors, typography, spacing } from '../theme';

const TONE_POR_ESTATUS = {
  Libre: 'success',
  Ocupada: 'danger',
  Reservada: 'warning',
};

export default function MesasScreen({ navigation }) {
  const [mesas, setMesas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [abriendo, setAbriendo] = useState(null);
  const [error, setError] = useState('');

  const cargarMesas = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getMesas();
      setMesas(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargarMesas();
    }, [cargarMesas])
  );

  const abrirMesa = async (mesa) => {
    if (abriendo !== null) return;
    setError('');
    const nuevoPedido = () =>
      navigation.navigate('Pedido', { mesaId: mesa.id, numeroMesa: mesa.numero_mesa });

    if (mesa.estatus.nombre !== 'Ocupada') {
      nuevoPedido();
      return;
    }

    setAbriendo(mesa.id);
    try {
      const activo = await getPedidoActivoDeMesa(mesa.id);
      if (activo) {
        navigation.navigate('Detalle', { pedidoId: activo.id, numeroMesa: mesa.numero_mesa });
      } else {
        nuevoPedido();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo abrir la mesa');
    } finally {
      setAbriendo(null);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Mesas</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={mesas}
        keyExtractor={(item) => item.id.toString()}
        numColumns={2}
        renderItem={({ item }) => (
          <View style={styles.cardWrap}>
            <Card onPress={() => abrirMesa(item)} style={item.id === abriendo ? styles.cardDisabled : null}>
              <Text style={styles.mesaNumero}>Mesa {item.numero_mesa}</Text>
              <Badge label={item.estatus.nombre} tone={TONE_POR_ESTATUS[item.estatus.nombre] || 'neutral'} />
              <Text style={styles.capacidad}>Capacidad: {item.capacidad}</Text>
              {abriendo === item.id ? <Text style={styles.capacidad}>Abriendo…</Text> : null}
            </Card>
          </View>
        )}
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
  cardWrap: { flex: 1, margin: spacing.xs },
  cardDisabled: { opacity: 0.6 },
  mesaNumero: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  capacidad: { color: colors.textSecondary, marginTop: spacing.sm, fontSize: typography.size.md },
});
