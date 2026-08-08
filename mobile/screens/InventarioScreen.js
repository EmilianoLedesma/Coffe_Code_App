import React, { useCallback, useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getIngredientes, createIngrediente, ajustarStock, deleteIngrediente } from '../api/ingredientes';
import { ApiError } from '../api/client';

export default function InventarioScreen() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');

  const [nombre, setNombre] = useState('');
  const [unidad, setUnidad] = useState('');
  const [stockMinimo, setStockMinimo] = useState('');
  const [costoUnitario, setCostoUnitario] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await getIngredientes());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const agregar = async () => {
    if (!nombre.trim() || !unidad.trim() || !stockMinimo || !costoUnitario) {
      setError('Completa nombre, unidad, stock mínimo y costo unitario');
      return;
    }

    setError('');
    try {
      await createIngrediente({
        nombre: nombre.trim(),
        unidad: unidad.trim(),
        stockMinimo: parseFloat(stockMinimo),
        costoUnitario: parseFloat(costoUnitario),
      });
      setNombre('');
      setUnidad('');
      setStockMinimo('');
      setCostoUnitario('');
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear el ingrediente');
    }
  };

  const subir = async (id) => {
    setError('');
    try {
      await ajustarStock(id, 1);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo ajustar el stock');
    }
  };

  const bajar = async (id) => {
    setError('');
    try {
      await ajustarStock(id, -1);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo ajustar el stock');
    }
  };

  const eliminar = async (id) => {
    setError('');
    setAviso('');
    try {
      const resultado = await deleteIngrediente(id);
      setAviso(resultado.mensaje);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el ingrediente');
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

      <Text style={styles.title}>Inventario</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {aviso ? <Text style={styles.aviso}>{aviso}</Text> : null}

      <TextInput placeholder="Nombre" value={nombre} onChangeText={setNombre} style={styles.input} />
      <TextInput placeholder="Unidad (g, ml, u)" value={unidad} onChangeText={setUnidad} style={styles.input} />
      <TextInput placeholder="Stock mínimo" value={stockMinimo} onChangeText={setStockMinimo} keyboardType="numeric" style={styles.input} />
      <TextInput placeholder="Costo unitario" value={costoUnitario} onChangeText={setCostoUnitario} keyboardType="numeric" style={styles.input} />

      <TouchableOpacity style={styles.btn} onPress={agregar}>
        <Text style={styles.btnText}>Agregar ingrediente</Text>
      </TouchableOpacity>

      <FlatList
        data={items}
        keyExtractor={(i) => i.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.card}>

            <Text style={styles.name}>{item.nombre}</Text>
            <Text>Stock: {item.stock_actual} {item.unidad}</Text>
            <Text style={item.stock_actual < item.stock_minimo ? styles.bajo : null}>
              Mínimo: {item.stock_minimo} {item.unidad}
            </Text>

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
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  aviso: { color: '#1F618D', marginBottom: 10 },
  input: { backgroundColor: 'white', padding: 10, marginBottom: 8, borderRadius: 8 },
  btn: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8, marginBottom: 10 },
  btnText: { color: 'white', textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 10, marginBottom: 10, borderRadius: 8 },
  name: { fontSize: 16, fontWeight: 'bold' },
  bajo: { color: '#C0392B', fontWeight: 'bold' },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  plus: { color: 'green', fontSize: 16 },
  minus: { color: 'orange', fontSize: 16 },
  delete: { color: 'red' }
});
