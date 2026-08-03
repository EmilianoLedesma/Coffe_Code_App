
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, FlatList } from 'react-native';

export default function CajaScreen({ navigation }) {

  const pedidos = [
    { id: 1, mesa: 'Mesa 1', total: 120 },
    { id: 2, mesa: 'Mesa 2', total: 85 },
    { id: 3, mesa: 'Mesa 3', total: 60 }
  ];

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Caja</Text>

      <FlatList
        data={pedidos}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingBottom: 30 }}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.mesa}>{item.mesa}</Text>
            <Text>Total: ${item.total}</Text>

            <TouchableOpacity
              style={styles.button}
              onPress={() =>
                navigation.navigate('Pago', {
                  pedido: {
                    mesa: item.mesa,
                    items: [
                      {
                        nombre: 'Consumo',
                        cantidad: 1,
                        precio: item.total
                      }
                    ],
                    estado: 'En preparación'
                  }
                })
              }
            >
              <Text style={{ color: 'white' }}>Cobrar</Text>
            </TouchableOpacity>

          </View>
        )}

        // 🔥 BOTÓN BIEN UBICADO (NO ABAJO PERDIDO)
        ListFooterComponent={() => (
          <TouchableOpacity
            style={[styles.button, { marginTop: 15, backgroundColor: '#444' }]}
            onPress={() => navigation.navigate('Gastos')}
          >
            <Text style={{ color: 'white' }}>Gastos y cuentas</Text>
          </TouchableOpacity>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#F5F5F5'
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 10
  },
  card: {
    backgroundColor: '#fff',
    padding: 15,
    marginBottom: 10,
    borderRadius: 10
  },
  mesa: {
    fontSize: 18,
    fontWeight: 'bold'
  },
  button: {
    marginTop: 10,
    backgroundColor: '#2E1B0F',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center'
  }
});