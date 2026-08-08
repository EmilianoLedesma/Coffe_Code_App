import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido, cambiarEstadoPedido } from '../api/pedidos';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';

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
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  if (error && !pedido) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error}</Text>
        <TouchableOpacity style={styles.button} onPress={cargar}>
          <Text style={styles.buttonText}>Reintentar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const puedeEntregar =
    (rol === 'Mesero' || rol === 'Administrador') && pedido.estatus.nombre === 'Listo';

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>

      <Text style={styles.title}>Pedido #{pedido.id} — Mesa {numeroMesa ?? pedido.id_mesa}</Text>
      <Text style={styles.estado}>Estado: {pedido.estatus.nombre}</Text>

      {pedido.detalle.map((item) => (
        <View key={item.id} style={styles.card}>
          <Text style={styles.producto}>{item.producto.nombre} x{item.cantidad}</Text>
          <Text>${item.precio_unitario} c/u</Text>
          <Text style={{ color: '#E67E22' }}>{item.estatus.nombre}</Text>
        </View>
      ))}

      {pedido.total !== null && (
        <Text style={styles.total}>Total: ${pedido.total}</Text>
      )}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {puedeEntregar && (
        <TouchableOpacity style={styles.entregar} onPress={marcarEntregado} disabled={entregando}>
          <Text style={styles.buttonText}>
            {entregando ? 'Actualizando...' : 'Marcar como Entregado'}
          </Text>
        </TouchableOpacity>
      )}

      <TouchableOpacity style={styles.button} onPress={cargar}>
        <Text style={styles.buttonText}>Actualizar</Text>
      </TouchableOpacity>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  estado: { fontSize: 16, fontWeight: 'bold', color: '#E67E22', marginBottom: 15 },
  error: { color: '#C0392B', marginBottom: 15, textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 15, borderRadius: 12, marginBottom: 10, elevation: 3 },
  producto: { fontSize: 16, fontWeight: 'bold' },
  total: { fontSize: 18, fontWeight: 'bold', marginTop: 10, marginBottom: 20 },
  entregar: { backgroundColor: '#27AE60', padding: 14, borderRadius: 10, alignItems: 'center', marginBottom: 10 },
  button: { backgroundColor: '#2E1B0F', padding: 14, borderRadius: 10, alignItems: 'center' },
  buttonText: { color: 'white', fontWeight: 'bold' },
});
