import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido } from '../api/pedidos_caja';
import { registrarVenta } from '../api/caja';
import { ApiError } from '../api/client';

const METODOS = [
  { key: 'Efectivo', label: 'Efectivo' },
  { key: 'Tarjeta débito', label: 'Tarjeta débito' },
  { key: 'Tarjeta crédito', label: 'Tarjeta crédito' },
  { key: 'Transferencia', label: 'Transferencia' },
];

export default function PagoScreen({ route, navigation }) {
  const { pedidoId } = route.params;

  const [pedido, setPedido] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metodoPago, setMetodoPago] = useState('');
  const [monto, setMonto] = useState('');
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState(null);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      getPedido(pedidoId)
        .then(setPedido)
        .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudo cargar el pedido'))
        .finally(() => setLoading(false));
    }, [pedidoId])
  );

  const subtotalEstimado = pedido
    ? pedido.detalle.reduce((acc, item) => acc + Number(item.precio_unitario) * item.cantidad, 0)
    : 0;

  const pagar = async () => {
    if (!metodoPago) {
      setError('Selecciona un método de pago');
      return;
    }
    if (!monto || Number(monto) <= 0) {
      setError('Ingresa el monto recibido');
      return;
    }

    setProcesando(true);
    setError('');
    try {
      const ticket = await registrarVenta({ pedidoId, metodoPago, monto: Number(monto) });
      setResultado(ticket);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo procesar el pago');
    } finally {
      setProcesando(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  if (resultado) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>Pago registrado</Text>
        <Text style={styles.text}>Total: ${resultado.total}</Text>
        <Text style={styles.text}>Cambio: ${resultado.pago.cambio}</Text>
        <TouchableOpacity style={styles.payButton} onPress={() => navigation.navigate('Caja')}>
          <Text style={styles.payText}>Volver a Caja</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>

      <Text style={styles.title}>Procesar Pago</Text>

      <View style={styles.card}>
        <Text style={styles.subtitle}>Mesa {pedido.id_mesa} — Pedido #{pedido.id}</Text>

        {pedido.detalle.map((item) => (
          <Text key={item.id} style={styles.text}>
            {item.producto.nombre} x{item.cantidad} — ${item.precio_unitario}
          </Text>
        ))}

        <Text style={styles.total}>Subtotal (sin IVA): ${subtotalEstimado.toFixed(2)}</Text>
        <Text style={{ color: 'gray' }}>El total final con IVA lo calcula el servidor al confirmar.</Text>
      </View>

      <Text style={styles.subtitle}>Método de pago</Text>

      <View style={styles.row}>
        {METODOS.map((m) => (
          <TouchableOpacity
            key={m.key}
            style={[styles.button, metodoPago === m.key && styles.buttonActive]}
            onPress={() => setMetodoPago(m.key)}
            disabled={procesando}
          >
            <Text style={styles.buttonText}>{m.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.card}>
        <Text>Monto recibido</Text>
        <TextInput
          style={styles.input}
          keyboardType="numeric"
          placeholder="Ej. 200"
          value={monto}
          onChangeText={setMonto}
          editable={!procesando}
        />
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity style={styles.payButton} onPress={pagar} disabled={procesando}>
        {procesando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.payText}>Confirmar y Pagar</Text>
        )}
      </TouchableOpacity>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5', padding: 15 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 15 },
  subtitle: { fontSize: 18, fontWeight: 'bold', marginTop: 10 },
  card: { backgroundColor: 'white', padding: 15, borderRadius: 10, marginBottom: 15 },
  text: { fontSize: 16 },
  total: { fontSize: 18, fontWeight: 'bold', marginTop: 10 },
  error: { color: '#C0392B', marginBottom: 10, textAlign: 'center' },
  row: { flexDirection: 'row', flexWrap: 'wrap', marginVertical: 10 },
  button: { backgroundColor: '#ccc', padding: 10, borderRadius: 8, width: '48%', alignItems: 'center', marginBottom: 8, marginRight: '2%' },
  buttonActive: { backgroundColor: '#2E1B0F' },
  buttonText: { color: 'white' },
  input: { borderWidth: 1, borderColor: '#ccc', marginTop: 10, padding: 10, borderRadius: 8 },
  payButton: { backgroundColor: '#2E1B0F', padding: 15, borderRadius: 10, marginTop: 10, alignItems: 'center' },
  payText: { color: 'white', fontWeight: 'bold' }
});
