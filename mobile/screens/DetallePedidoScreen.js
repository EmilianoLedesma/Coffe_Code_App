import React, { useState } from 'react';
import { View, Text, TouchableOpacity, Alert, StyleSheet, ScrollView } from 'react-native';

export default function DetallePedidoScreen() {

  const [estado, setEstado] = useState('En preparación');

  const cambiarEstado = (nuevo) => {
    setEstado(nuevo);

    Alert.alert(
      'Estado actualizado',
      `El pedido ahora está: ${nuevo}`
    );
  };

  const guardar = () => {
    Alert.alert(
      'Pedido guardado',
      `Estado actual: ${estado}`
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      <Text style={styles.title}>Detalle del Pedido</Text>

      <Text style={styles.label}>Estado actual:</Text>
      <Text style={styles.estado}>{estado}</Text>

      <TouchableOpacity style={styles.btn} onPress={() => cambiarEstado('En preparación')}>
        <Text style={styles.btnText}>En preparación</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.btn} onPress={() => cambiarEstado('Listo')}>
        <Text style={styles.btnText}>Listo</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.btn} onPress={() => cambiarEstado('Entregado')}>
        <Text style={styles.btnText}>Entregado</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.saveBtn} onPress={guardar}>
        <Text style={styles.saveText}>GUARDAR CAMBIOS</Text>
      </TouchableOpacity>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5'
  },

  content: {
    padding: 20,
    paddingBottom: 80
  },

  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 20
  },

  label: {
    fontSize: 16
  },

  estado: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 20
  },

  btn: {
    backgroundColor: '#ccc',
    padding: 12,
    borderRadius: 8,
    marginBottom: 10
  },

  btnText: {
    textAlign: 'center',
    fontWeight: 'bold'
  },

  saveBtn: {
    backgroundColor: '#2E1B0F',
    padding: 15,
    borderRadius: 10,
    marginTop: 25,
    alignItems: 'center'
  },

  saveText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16
  }
});