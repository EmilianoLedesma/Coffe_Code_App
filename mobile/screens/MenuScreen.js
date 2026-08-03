import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, Alert, StyleSheet } from 'react-native';

export default function MenuScreen() {

  const [productos, setProductos] = useState([
    { id: '1', nombre: 'Café Americano', precio: 35, descripcion: 'Café negro clásico' },
    { id: '2', nombre: 'Capuccino', precio: 45, descripcion: 'Con leche espumada' }
  ]);

  const [nombre, setNombre] = useState('');
  const [precio, setPrecio] = useState('');
  const [descripcion, setDescripcion] = useState('');

  const agregarProducto = () => {
    if (!nombre || !precio) {
      Alert.alert('Error', 'Completa los campos');
      return;
    }

    const nuevo = {
      id: Date.now().toString(),
      nombre,
      precio: parseFloat(precio),
      descripcion
    };

    setProductos([...productos, nuevo]);

    Alert.alert('Éxito', 'Producto agregado al menú');

    setNombre('');
    setPrecio('');
    setDescripcion('');
  };

  const eliminar = (id) => {
    setProductos(productos.filter(p => p.id !== id));
  };

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Gestión de Menú</Text>

      <TextInput placeholder="Nombre" value={nombre} onChangeText={setNombre} style={styles.input}/>
      <TextInput placeholder="Precio" value={precio} onChangeText={setPrecio} keyboardType="numeric" style={styles.input}/>
      <TextInput placeholder="Descripción" value={descripcion} onChangeText={setDescripcion} style={styles.input}/>

      <TouchableOpacity style={styles.btn} onPress={agregarProducto}>
        <Text style={styles.btnText}>Agregar producto</Text>
      </TouchableOpacity>

      <FlatList
        data={productos}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.name}>{item.nombre}</Text>
            <Text>${item.precio}</Text>
            <Text>{item.descripcion}</Text>

            <TouchableOpacity onPress={() => eliminar(item.id)}>
              <Text style={{ color: 'red', marginTop: 5 }}>Eliminar</Text>
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
  input: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  btn: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8, marginBottom: 10 },
  btnText: { color: 'white', textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  name: { fontSize: 16, fontWeight: 'bold' }
});