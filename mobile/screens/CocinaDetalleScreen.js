import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido, cambiarEstadoPedido } from '../api/pedidos_cocina';
import { ApiError } from '../api/client';

const SIGUIENTE_ESTATUS = {
  Pendiente: 'En preparación',
  'En preparación': 'Listo',
};

export default function CocinaDetalleScreen({ route, navigation }) {
  const { pedidoId } = route.params;
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
      if (actualizado.alertas_stock_bajo && actualizado.alertas_stock_bajo.length > 0) {
        setError(`Alerta de stock bajo: ${actualizado.alertas_stock_bajo.join(', ')}`);
      }
      if (siguiente === 'Listo') {
        navigation.goBack();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cambiar el estatus');
    } finally {
      setCambiando(false);
    }
  };

  if (loading || !pedido) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  const siguiente = SIGUIENTE_ESTATUS[pedido.estatus.nombre];

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>

      <Text style={styles.title}>Pedido #{pedido.id} — Mesa {pedido.id_mesa}</Text>
      <Text style={styles.estado}>Estado: {pedido.estatus.nombre}</Text>

      {pedido.detalle.map((item) => (
        <View key={item.id} style={styles.card}>
          <Text style={styles.producto}>{item.producto.nombre} x{item.cantidad}</Text>
          {item.especificaciones ? <Text style={{ color: 'gray' }}>{item.especificaciones}</Text> : null}
        </View>
      ))}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {siguiente ? (
        <TouchableOpacity style={styles.button} onPress={avanzarEstado} disabled={cambiando}>
          <Text style={styles.buttonText}>
            {cambiando ? 'Actualizando...' : `Marcar como ${siguiente}`}
          </Text>
        </TouchableOpacity>
      ) : (
        <Text style={{ color: 'gray', textAlign: 'center' }}>No hay más transiciones desde cocina</Text>
      )}

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  estado: { fontSize: 16, fontWeight: 'bold', color: '#E67E22', marginBottom: 15 },
  error: { color: '#C0392B', marginBottom: 15, textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 15, borderRadius: 12, marginBottom: 10, elevation: 3 },
  producto: { fontSize: 16, fontWeight: 'bold' },
  button: { backgroundColor: '#2E1B0F', padding: 14, borderRadius: 10, alignItems: 'center', marginTop: 10 },
  buttonText: { color: 'white', fontWeight: 'bold' },
});
