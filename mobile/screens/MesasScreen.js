import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getMesas } from '../api/mesas';
import { getPedidoActivoDeMesa } from '../api/pedidos';
import { ApiError } from '../api/client';

const COLOR_POR_ESTATUS = {
  Libre: '#27AE60',
  Ocupada: '#C0392B',
  Reservada: '#E67E22',
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
        <ActivityIndicator size="large" color="#2E1B0F" />
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
          <TouchableOpacity
            style={[styles.card, { borderColor: COLOR_POR_ESTATUS[item.estatus.nombre] || '#999' }]}
            onPress={() => abrirMesa(item)}
            disabled={abriendo !== null}
          >
            <Text style={styles.mesaNumero}>Mesa {item.numero_mesa}</Text>
            <Text style={{ color: COLOR_POR_ESTATUS[item.estatus.nombre] || '#999', fontWeight: 'bold' }}>
              {item.estatus.nombre}
            </Text>
            <Text style={styles.capacidad}>Capacidad: {item.capacidad}</Text>
            {abriendo === item.id ? <Text style={styles.capacidad}>Abriendo…</Text> : null}
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5', padding: 15 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 15, textAlign: 'center' },
  error: { color: '#C0392B', textAlign: 'center', marginBottom: 10 },
  card: {
    flex: 1,
    backgroundColor: 'white',
    margin: 6,
    padding: 15,
    borderRadius: 12,
    borderWidth: 2,
    elevation: 3,
  },
  mesaNumero: { fontSize: 18, fontWeight: 'bold', marginBottom: 4 },
  capacidad: { color: 'gray', marginTop: 4 },
});
