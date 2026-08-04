import React, { useCallback, useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getProductos, createProducto, deleteProducto } from '../api/productos';
import { getCategorias } from '../api/categorias';
import { ApiError } from '../api/client';

export default function MenuScreen() {
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [categoriaId, setCategoriaId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [nombre, setNombre] = useState('');
  const [precio, setPrecio] = useState('');
  const [descripcion, setDescripcion] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [prods, cats] = await Promise.all([getProductos(), getCategorias()]);
      setProductos(prods);
      setCategorias(cats);
      if (cats.length > 0 && categoriaId === null) setCategoriaId(cats[0].id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, [categoriaId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const agregarProducto = async () => {
    if (!nombre.trim() || !precio || !categoriaId) {
      setError('Completa nombre, precio y categoría');
      return;
    }

    setError('');
    try {
      await createProducto({
        nombre: nombre.trim(),
        descripcion: descripcion.trim(),
        precioVenta: parseFloat(precio),
        idCategoria: categoriaId,
      });
      setNombre('');
      setPrecio('');
      setDescripcion('');
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear el producto');
    }
  };

  const eliminar = async (id) => {
    setError('');
    try {
      await deleteProducto(id);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el producto');
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E1B0F" />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Gestión de Menú</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TextInput placeholder="Nombre" value={nombre} onChangeText={setNombre} style={styles.input} />
      <TextInput placeholder="Precio" value={precio} onChangeText={setPrecio} keyboardType="numeric" style={styles.input} />
      <TextInput placeholder="Descripción" value={descripcion} onChangeText={setDescripcion} style={styles.input} />

      <View style={styles.categorias}>
        {categorias.map((cat) => (
          <TouchableOpacity key={cat.id} onPress={() => setCategoriaId(cat.id)}>
            <Text style={categoriaId === cat.id ? styles.categoriaSelected : styles.categoria}>
              {cat.nombre}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity style={styles.btn} onPress={agregarProducto}>
        <Text style={styles.btnText}>Agregar producto</Text>
      </TouchableOpacity>

      <FlatList
        data={productos}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.name}>{item.nombre}</Text>
            <Text>${item.precio_venta}</Text>
            <Text>{item.categoria.nombre}</Text>

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
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  input: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  categorias: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 10 },
  categoria: { padding: 8, marginRight: 8, marginBottom: 8, borderRadius: 8, borderWidth: 1, borderColor: '#ddd', color: 'gray' },
  categoriaSelected: { padding: 8, marginRight: 8, marginBottom: 8, borderRadius: 8, backgroundColor: '#2E1B0F', color: 'white' },
  btn: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8, marginBottom: 10 },
  btnText: { color: 'white', textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  name: { fontSize: 16, fontWeight: 'bold' }
});
