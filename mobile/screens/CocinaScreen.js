import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

export default function CocinaScreen({ navigation }) {
  return (
    <View style={styles.container}>

      <Text style={styles.title}> Cocina</Text>
      <Text style={styles.subtitle}>Gestión operativa de pedidos</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Estado del sistema</Text>
        <Text>Cocina activa</Text>
        <Text>Pedidos en espera: 3</Text>
      </View>

      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate('ColaPedidos')}
      >
        <Text style={styles.buttonText}>Cola de pedidos</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate('Menu')}
      >
        <Text style={styles.buttonText}> Gestión de menú</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate('Inventario')}
      >
        <Text style={styles.buttonText}> Inventario</Text>
      </TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#F5F5F5' },
  title: { fontSize: 26, fontWeight: 'bold', marginBottom: 5 },
  subtitle: { color: 'gray', marginBottom: 20 },

  card: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 12,
    marginBottom: 20,
    elevation: 3
  },

  cardTitle: {
    fontWeight: 'bold',
    marginBottom: 5
  },

  button: {
    backgroundColor: '#2E1B0F',
    padding: 15,
    borderRadius: 10,
    marginBottom: 12
  },

  buttonText: {
    color: 'white',
    fontSize: 16,
    textAlign: 'center'
  }
});