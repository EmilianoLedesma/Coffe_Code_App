import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, FlatList, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedidosListos } from '../api/pedidos_caja';
import { getMesas } from '../api/mesas';
import { ApiError } from '../api/client';
import { connectToChannel } from '../ws/client';

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

      <Text style={styles.title}>Caja</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={pedidos}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingBottom: 30 }}
        ListEmptyComponent={<Text style={{ textAlign: 'center', color: 'gray' }}>Sin pedidos listos para cobrar</Text>}
        renderItem={({ item }) => {
          // registrar_venta pone `total` pero deja el estatus en `Listo`
          // (api/app/services/ventas.py:63): el pedido sigue en esta cola
          // hasta que el Mesero lo marque Entregado. Ofrecerle "Cobrar" otra
          // vez garantiza un 409 de pago duplicado.
          const pagado = item.total !== null;
          return (
            <View style={[styles.card, pagado && styles.cardPagado]}>
              <Text style={styles.mesa}>Mesa {numeroPorMesa[item.id_mesa] ?? item.id_mesa}</Text>
              <Text>Pedido #{item.id} — {item.detalle.length} ítem(s)</Text>

              {pagado ? (
                <Text style={styles.pagado}>
                  Cobrado (${item.total}) — pendiente de entrega por el mesero
                </Text>
              ) : (
                <TouchableOpacity
                  style={styles.button}
                  onPress={() =>
                    navigation.navigate('Pago', {
                      pedidoId: item.id,
                      numeroMesa: numeroPorMesa[item.id_mesa],
                    })
                  }
                >
                  <Text style={{ color: 'white' }}>Cobrar</Text>
                </TouchableOpacity>
              )}
            </View>
          );
        }}
        ListFooterComponent={() => (
          <View>
            <TouchableOpacity
              style={[styles.button, { marginTop: 15, backgroundColor: '#444' }]}
              onPress={() => navigation.navigate('Gastos')}
            >
              <Text style={{ color: 'white' }}>Gastos y cuentas</Text>
            </TouchableOpacity>
            {/* Task 4 agrega aquí el botón "Registrar compra de insumo",
                junto con la ruta `Compras` que necesita para no crashear. */}
          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#F5F5F5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  card: { backgroundColor: '#fff', padding: 15, marginBottom: 10, borderRadius: 10 },
  cardPagado: { opacity: 0.6 },
  pagado: { marginTop: 8, color: '#1F618D', fontWeight: 'bold' },
  mesa: { fontSize: 18, fontWeight: 'bold' },
  button: { marginTop: 10, backgroundColor: '#2E1B0F', padding: 10, borderRadius: 8, alignItems: 'center' }
});
