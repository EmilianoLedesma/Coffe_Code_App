import React from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity } from 'react-native';

export default function ColaPedidosScreen({ navigation }) {

  const pedidos = [
    { id: 1, mesa: 1, items: 3, estado: 'En cocina', prioridad: 'Alta' },
    { id: 2, mesa: 2, items: 2, estado: 'En cocina', prioridad: 'Media' },
    { id: 3, mesa: 5, items: 4, estado: 'En espera', prioridad: 'Alta' }
  ];

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Cola de Pedidos</Text>

      <FlatList
        data={pedidos}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.card}>

            <Text style={styles.mesa}>Mesa {item.mesa}</Text>

            <Text>Items: {item.items}</Text>
            <Text>Estado: {item.estado}</Text>
            <Text>Prioridad: {item.prioridad}</Text>

            <TouchableOpacity
              style={styles.button}
              onPress={() => navigation.navigate('Detalle', { pedidoId: item.id })}
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

  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },

  card: {
    backgroundColor: 'white',
    padding: 15,
    marginBottom: 12,
    borderRadius: 12
  },

  mesa: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 5
  },

  button: {
    marginTop: 10,
    backgroundColor: '#2E1B0F',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center'
  }
});