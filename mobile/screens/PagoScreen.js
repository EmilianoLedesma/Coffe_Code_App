import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator
} from 'react-native';

export default function PagoScreen({ route }) {

  const pedido = route?.params?.pedido || {
    mesa: 1,
    items: [
      { nombre: 'Café', cantidad: 2, precio: 35 },
      { nombre: 'Pan', cantidad: 1, precio: 20 }
    ],
    estado: 'En preparación'
  };

  const [metodoPago, setMetodoPago] = useState('');
  const [monto, setMonto] = useState('');
  const [procesando, setProcesando] = useState(false);

  const total = pedido.items.reduce(
    (acc, item) => acc + item.precio * item.cantidad,
    0
  );

  const pagar = () => {
    if (!metodoPago) {
      alert('Error. Selecciona un método de pago');
      return;
    }

    if (metodoPago === 'efectivo' && Number(monto) < total) {
      alert('Error. Monto insuficiente');
      return;
    }

    setProcesando(true);

    setTimeout(() => {
      setProcesando(false);

      alert(
        
        `La mesa ${pedido.mesa} ha sido cobrada correctamente.\nTotal: $${total}\nMétodo: ${metodoPago}`
      );

      setMetodoPago('');
      setMonto('');
    }, 2000);
  };

  return (
    <ScrollView style={styles.container}>

      <Text style={styles.title}>Procesar Pago</Text>

      {/* DETALLE */}
      <View style={styles.card}>
        <Text style={styles.subtitle}>Mesa {pedido.mesa}</Text>

        {pedido.items.map((item, index) => (
          <Text key={index} style={styles.text}>
            {item.nombre} x{item.cantidad}
          </Text>
        ))}

        <Text style={styles.total}>Total: ${total}</Text>
      </View>

      {/* MÉTODOS */}
      <Text style={styles.subtitle}>Método de pago</Text>

      <View style={styles.row}>
        <TouchableOpacity
          style={[styles.button, metodoPago === 'efectivo' && styles.buttonActive]}
          onPress={() => setMetodoPago('efectivo')}
          disabled={procesando}
        >
          <Text style={styles.buttonText}>Efectivo</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, metodoPago === 'tarjeta' && styles.buttonActive]}
          onPress={() => setMetodoPago('tarjeta')}
          disabled={procesando}
        >
          <Text style={styles.buttonText}>Tarjeta</Text>
        </TouchableOpacity>
      </View>

      {/* EFECTIVO */}
      {metodoPago === 'efectivo' && (
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
      )}

      {/* TARJETA */}
      {metodoPago === 'tarjeta' && (
        <View style={styles.card}>
          <Text>Simulación tarjeta</Text>

          <TextInput style={styles.input} placeholder="Número de tarjeta" editable={!procesando} />
          <TextInput style={styles.input} placeholder="Nombre del titular" editable={!procesando} />
          <TextInput style={styles.input} placeholder="CVV" keyboardType="numeric" editable={!procesando} />
        </View>
      )}

      {/* BOTÓN */}
      <TouchableOpacity
        style={styles.payButton}
        onPress={pagar}
        disabled={procesando}
      >
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
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    padding: 15
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 15
  },
  subtitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 10
  },
  card: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15
  },
  text: {
    fontSize: 16
  },
  total: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 10
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 10
  },
  button: {
    backgroundColor: '#ccc',
    padding: 10,
    borderRadius: 8,
    width: '48%',
    alignItems: 'center'
  },
  buttonActive: {
    backgroundColor: '#2E1B0F'
  },
  buttonText: {
    color: 'white'
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    marginTop: 10,
    padding: 10,
    borderRadius: 8
  },
  payButton: {
    backgroundColor: '#2E1B0F',
    padding: 15,
    borderRadius: 10,
    marginTop: 10,
    alignItems: 'center'
  },
  payText: {
    color: 'white',
    fontWeight: 'bold'
  }
});