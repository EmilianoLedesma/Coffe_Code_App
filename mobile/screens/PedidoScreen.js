import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, Alert } from 'react-native';

export default function PedidoScreen({ route, navigation }) {

  const { mesaId } = route.params;

  const menu = [
    { id: 1, nombre: 'Café' },
    { id: 2, nombre: 'Pan' },
    { id: 3, nombre: 'Pastel' },
    { id: 4, nombre: 'Té' }
  ];

  const [pedido, setPedido] = useState([
    { nombre: 'Café', cantidad: 2 }
  ]);

  const agregarProducto = (producto) => {
    const existe = pedido.find(p => p.nombre === producto.nombre);

    if (existe) {
      setPedido(
        pedido.map(p =>
          p.nombre === producto.nombre
            ? { ...p, cantidad: p.cantidad + 1 }
            : p
        )
      );
    } else {
      setPedido([...pedido, { nombre: producto.nombre, cantidad: 1 }]);
    }
  };

  const guardarPedido = () => {
    Alert.alert(
      'Pedido guardado',
      `Mesa ${mesaId} actualizada`,
      [
        {
          text: 'OK',
          onPress: () => navigation.navigate('EstadoPedido', { mesaId })
        }
      ]
    );
  };

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Mesa {mesaId}</Text>

      {/* PEDIDO ACTUAL */}
      <Text style={styles.subtitle}>Pedido actual</Text>

      {pedido.map((item, index) => (
        <Text key={index}>
          {item.nombre} x{item.cantidad}
        </Text>
      ))}

      {/* MENÚ */}
      <Text style={styles.subtitle}>Menú</Text>

      <FlatList
        data={menu}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.item}
            onPress={() => agregarProducto(item)}
          >
            <Text>{item.nombre}</Text>
            <Text style={{ fontWeight: 'bold' }}>+</Text>
          </TouchableOpacity>
        )}
      />

      <TouchableOpacity
        style={styles.button}
        onPress={guardarPedido}
      >
        <Text style={{ color: 'white', fontWeight: 'bold' }}>
          ✔ Guardar / Finalizar pedido
        </Text>
      </TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    flex: 1,
    padding: 20
  },

  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center'
  },

  subtitle: {
    marginTop: 15,
    fontSize: 16,
    fontWeight: 'bold'
  },

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