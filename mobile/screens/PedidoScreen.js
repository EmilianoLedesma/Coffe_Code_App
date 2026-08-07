import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { getProductos } from '../api/productos';
import { crearPedido } from '../api/pedidos';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export default function PedidoScreen({ route, navigation }) {
  const { mesaId, numeroMesa } = route.params;
  const { userId } = useAuth();

  const [menu, setMenu] = useState([]);
  const [pedido, setPedido] = useState([]);
  const [loadingMenu, setLoadingMenu] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const productos = await getProductos();
        // GET /productos solo filtra por `activo`; los `disponible:false`
        // llegan igual y provocarían un 409 tardío al Guardar
        // (api/app/services/pedidos.py:64-71). Se filtran aquí.
        setMenu(productos.filter((p) => p.disponible !== false));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'No se pudo cargar el menú');
      } finally {
        setLoadingMenu(false);
      }
    })();
  }, []);

  const agregarProducto = (producto) => {
    setPedido((actual) => {
      const existe = actual.find((p) => p.id_producto === producto.id);
      if (existe) {
        return actual.map((p) =>
          p.id_producto === producto.id ? { ...p, cantidad: p.cantidad + 1 } : p
        );
      }
      return [...actual, { id_producto: producto.id, nombre: producto.nombre, cantidad: 1 }];
    });
  };

  const guardarPedido = async () => {
    if (pedido.length === 0) {
      setError('El pedido no puede estar vacío');
      return;
    }

    setGuardando(true);
    setError('');
    try {
      const creado = await crearPedido({ mesaId, usuarioId: userId, items: pedido });
      navigation.navigate('Detalle', { pedidoId: creado.id, numeroMesa });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el pedido');
    } finally {
      setGuardando(false);
    }
  };

  if (loadingMenu) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Mesa {numeroMesa ?? mesaId}</Text>

      <Text style={styles.subtitle}>Pedido actual</Text>
      {pedido.length === 0 ? (
        <Text style={{ color: 'gray' }}>Sin productos aún</Text>
      ) : (
        pedido.map((item) => (
          <Text key={item.id_producto}>{item.nombre} x{item.cantidad}</Text>
        ))
      )}

      <Text style={styles.subtitle}>Menú</Text>

      <FlatList
        data={menu}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.item} onPress={() => agregarProducto(item)}>
            <Text>{item.nombre} — ${item.precio_venta}</Text>
            <Text style={{ fontWeight: 'bold' }}>+</Text>
          </TouchableOpacity>
        )}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity style={styles.button} onPress={guardarPedido} disabled={guardando}>
        <Text style={{ color: 'white', fontWeight: 'bold' }}>
          {guardando ? 'Guardando...' : '✔ Guardar / Finalizar pedido'}
        </Text>
      </TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 24, fontWeight: 'bold', textAlign: 'center' },
  subtitle: { marginTop: 15, fontSize: 16, fontWeight: 'bold' },
  error: { color: '#C0392B', marginTop: 10, textAlign: 'center' },
  item: {
    padding: 15,
    backgroundColor: '#eee',
    marginVertical: 5,
    borderRadius: 10,
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  button: {
    backgroundColor: '#2E1B0F',
    padding: 12,
    borderRadius: 10,
    marginTop: 20,
    alignItems: 'center'
  }
});
