import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView
} from 'react-native';

export default function EstadoPedidoScreen() {

  const [mesa, setMesa] = useState('');
  const [producto, setProducto] = useState('');
  const [cantidad, setCantidad] = useState('');
  const [precio, setPrecio] = useState('');

  const pedidos = [
    { id: 1, mesa: 1, producto: 'Café', cantidad: 2, precio: 25, estado: 'En preparación' },
    { id: 2, mesa: 2, producto: 'Pan', cantidad: 1, precio: 15, estado: 'Listo' }
  ];

  const agregarPedido = () => {

    if (!mesa || !producto || !cantidad || !precio) {
      Alert.alert('Error', 'Faltan campos');
      return;
    }

    const total = Number(cantidad) * Number(precio);

    Alert.alert(
      'Pedido agregado',
      `Mesa ${mesa} - ${producto} x${cantidad}\nTotal: $${total}`
    );

    setProducto('');
    setCantidad('');
    setPrecio('');
  };

  const guardarPedido = () => {

    if (!mesa || !producto || !cantidad || !precio) {
      Alert.alert('Error', 'No puedes guardar vacío');
      return;
    }

    const total = Number(cantidad) * Number(precio);

    Alert.alert(
      'Guardado',
      `Mesa ${mesa}\nTotal: $${total}`
    );
  };

  return (
    <ScrollView style={styles.container}>

      <Text style={styles.title}>Estado de pedidos</Text>

      {/* 🔥 DETALLES POR MESA */}
      <Text style={styles.section}>Mesa 1</Text>
      <View style={styles.card}>
        <Text style={styles.text}>Café x2 - $25 c/u</Text>
        <Text style={styles.total}>Total: $50</Text>
        <Text style={styles.estado}>En preparación</Text>
      </View>

      <Text style={styles.section}>Mesa 2</Text>
      <View style={styles.card}>
        <Text style={styles.text}>Pan x1 - $15</Text>
        <Text style={styles.total}>Total: $15</Text>
        <Text style={styles.estadoListo}>Listo</Text>
      </View>

      {/* 🔥 FORMULARIO */}
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

        <TextInput
          placeholder="Precio unitario"
          value={precio}
          onChangeText={setPrecio}
          keyboardType="numeric"
          style={styles.input}
        />

      </View>

      {/* BOTONES */}
      <TouchableOpacity style={styles.button} onPress={agregarPedido}>
        <Text style={styles.buttonText}>Agregar pedido</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.buttonSave} onPress={guardarPedido}>
        <Text style={styles.buttonText}>Guardar pedido</Text>
      </TouchableOpacity>

    </ScrollView>
  );
}

const styles = StyleSheet.create({

  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    padding: 20
  },

  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2E1B0F',
    textAlign: 'center',
    marginBottom: 15
  },

  section: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 10,
    marginBottom: 5,
    color: '#2E1B0F'
  },

  card: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 15,
    marginBottom: 10,
    elevation: 4
  },

  text: {
    fontSize: 16,
    fontWeight: 'bold'
  },

  total: {
    marginTop: 5,
    fontWeight: 'bold',
    color: '#2980B9'
  },

  estado: {
    marginTop: 5,
    color: '#E67E22',
    fontWeight: 'bold'
  },

  estadoListo: {
    marginTop: 5,
    color: '#27AE60',
    fontWeight: 'bold'
  },

  form: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 15,
    marginTop: 15,
    elevation: 4
  },

  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 10,
    borderRadius: 10,
    marginBottom: 10
  },

  button: {
    backgroundColor: '#2E1B0F',
    padding: 14,
    borderRadius: 10,
    marginTop: 10
  },

  buttonSave: {
    backgroundColor: '#6b3b1a',
    padding: 14,
    borderRadius: 10,
    marginTop: 10
  },

  buttonText: {
    color: 'white',
    textAlign: 'center',
    fontWeight: 'bold'
  }

});