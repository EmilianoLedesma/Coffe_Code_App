import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert
} from 'react-native';

export default function EstadoPedidoScreen() {

  const [mesa, setMesa] = useState('');
  const [producto, setProducto] = useState('');
  const [cantidad, setCantidad] = useState('');

  const agregarPedido = () => {

    if (!mesa.trim() || !producto.trim() || !cantidad.trim()) {
      Alert.alert('Error', 'Debes llenar todos los campos');
      return;
    }

    if (isNaN(cantidad) || Number(cantidad) <= 0) {
      Alert.alert('Error', 'La cantidad debe ser un número mayor a 0');
      return;
    }

    Alert.alert('Éxito', `Pedido agregado: ${producto} x${cantidad}`);
  };

  const guardarPedido = () => {

    if (!mesa.trim()) {
      Alert.alert('Error', 'Debes ingresar la mesa');
      return;
    }

    Alert.alert('Éxito', `Pedido guardado en mesa ${mesa}`);
  };

  return (

    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >

      <ScrollView contentContainerStyle={styles.container}>

        <Text style={styles.title}>Estado de pedidos</Text>

        {/* LISTA (ejemplo) */}
        <View style={styles.card}>
          <Text>Mesa 1 - Café x2</Text>
          <Text style={styles.estado}>En preparación</Text>
        </View>

        <View style={styles.card}>
          <Text>Mesa 2 - Pan x1</Text>
          <Text style={styles.listo}>Listo</Text>
        </View>

        {/* FORMULARIO */}
        <View style={styles.form}>

          <TextInput
            placeholder="Mesa"
            value={mesa}
            onChangeText={setMesa}
            style={styles.input}
          />

          <TextInput
            placeholder="Producto"
            value={producto}
            onChangeText={setProducto}
            style={styles.input}
          />

          <TextInput
            placeholder="Cantidad"
            value={cantidad}
            onChangeText={setCantidad}
            keyboardType="numeric"
            style={styles.input}
          />

        </View>

        {/* BOTONES */}
        <TouchableOpacity style={styles.button} onPress={agregarPedido}>
          <Text style={styles.buttonText}>Agregar pedido</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.saveButton} onPress={guardarPedido}>
          <Text style={styles.saveText}>Guardar pedido</Text>
        </TouchableOpacity>

      </ScrollView>

    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: '#F5F5F5',
    padding: 20,
  },

  title: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#2E1B0F',
    marginBottom: 15,
    textAlign: 'center',
  },

  card: {
    width: '100%',
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 15,
    marginBottom: 10,
    elevation: 4,
  },

  estado: {
    marginTop: 5,
    color: '#E67E22',
    fontWeight: 'bold',
  },

  listo: {
    marginTop: 5,
    color: '#27AE60',
    fontWeight: 'bold',
  },

  form: {
    width: '100%',
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 15,
    marginTop: 20,
    elevation: 4,
  },

  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 12,
    marginBottom: 10,
    borderRadius: 10,
    backgroundColor: '#FAFAFA',
  },

  button: {
    backgroundColor: '#2E1B0F',
    padding: 14,
    borderRadius: 10,
    marginTop: 15,
    width: '100%',
    elevation: 3,
  },

  buttonText: {
    color: 'white',
    textAlign: 'center',
    fontWeight: 'bold',
  },

  saveButton: {
    backgroundColor: '#632a04',
    padding: 14,
    borderRadius: 10,
    marginTop: 10,
    width: '100%',
    elevation: 3,
  },

  saveText: {
    color: 'white',
    textAlign: 'center',
    fontWeight: 'bold',
  },
});