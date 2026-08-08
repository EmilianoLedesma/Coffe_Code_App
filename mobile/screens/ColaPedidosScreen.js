import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getColaPendientes } from '../api/pedidos_cocina';
import { getMesas } from '../api/mesas';
import { ApiError } from '../api/client';
import { connectToChannel } from '../ws/client';

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

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
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
        renderItem={({ item }) => (
          <View style={styles.card}>

            <Text style={styles.mesa}>Mesa {numeroPorMesa[item.id_mesa] ?? item.id_mesa}</Text>
            <Text>Items: {item.detalle.length}</Text>
            <Text>Estado: {item.estatus.nombre}</Text>

            <TouchableOpacity
              style={styles.button}
              onPress={() =>
                navigation.navigate('CocinaDetalle', {
                  pedidoId: item.id,
                  numeroMesa: numeroPorMesa[item.id_mesa],
                })
              }
            >
              <Text style={{ color: 'white' }}>Ver preparación</Text>
            </TouchableOpacity>

          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 15, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  card: { backgroundColor: 'white', padding: 15, marginBottom: 12, borderRadius: 12 },
  mesa: { fontSize: 18, fontWeight: 'bold', marginBottom: 5 },
  button: { marginTop: 10, backgroundColor: '#2E1B0F', padding: 10, borderRadius: 8, alignItems: 'center' }
});
