import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, Alert, StyleSheet } from 'react-native';

export default function InventarioScreen() {

  const [items, setItems] = useState([
    { id: '1', nombre: 'Café en grano', stock: 10, marca: 'Arabica', proveedor: 'Proveedor A' },
    { id: '2', nombre: 'Leche', stock: 20, marca: 'Lala', proveedor: 'Proveedor B' }
  ]);

  const [nombre, setNombre] = useState('');
  const [marca, setMarca] = useState('');
  const [proveedor, setProveedor] = useState('');

  const agregar = () => {
    if (!nombre) return Alert.alert('Error', 'Nombre requerido');

    const nuevo = {
      id: Date.now().toString(),
      nombre,
      stock: 0,
      marca,
      proveedor
    };

    setItems([...items, nuevo]);
    Alert.alert('Agregado', 'Producto en inventario');

    setNombre('');
    setMarca('');
    setProveedor('');
  };

  const subir = (id) => {
    setItems(items.map(i =>
      i.id === id ? { ...i, stock: i.stock + 1 } : i
    ));
  };

  const bajar = (id) => {
    setItems(items.map(i =>
      i.id === id && i.stock > 0
        ? { ...i, stock: i.stock - 1 }
        : i
    ));
  };

  const eliminar = (id) => {
    setItems(items.filter(i => i.id !== id));
  };

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Inventario</Text>

      <TextInput placeholder="Nombre" value={nombre} onChangeText={setNombre} style={styles.input}/>
      <TextInput placeholder="Marca" value={marca} onChangeText={setMarca} style={styles.input}/>
      <TextInput placeholder="Proveedor" value={proveedor} onChangeText={setProveedor} style={styles.input}/>

      <TouchableOpacity style={styles.btn} onPress={agregar}>
        <Text style={styles.btnText}>Agregar producto</Text>
      </TouchableOpacity>

      <FlatList
        data={items}
        keyExtractor={i => i.id}
        renderItem={({ item }) => (
          <View style={styles.card}>

            <Text style={styles.name}>{item.nombre}</Text>
            <Text>Stock: {item.stock}</Text>
            <Text>Marca: {item.marca}</Text>
            <Text>Proveedor: {item.proveedor}</Text>

            <View style={styles.row}>
              <TouchableOpacity onPress={() => subir(item.id)}>
                <Text style={styles.plus}>+1</Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={() => bajar(item.id)}>
                <Text style={styles.minus}>-1</Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={() => eliminar(item.id)}>
                <Text style={styles.delete}>Eliminar</Text>
              </TouchableOpacity>
            </View>

          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 15, backgroundColor: '#F5F5F5' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  input: { backgroundColor: 'white', padding: 10, marginBottom: 8, borderRadius: 8 },
  btn: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8, marginBottom: 10 },
  btnText: { color: 'white', textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  name: { fontSize: 16, fontWeight: 'bold' },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  plus: { color: 'green', fontSize: 16 },
  minus: { color: 'orange', fontSize: 16 },
  delete: { color: 'red' }
});