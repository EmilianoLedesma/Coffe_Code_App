import React, { useCallback, useState } from 'react';
import { View, Text, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { getProductos, createProducto, deleteProducto } from '../api/productos';
import { getCategorias } from '../api/categorias';
import { ApiError } from '../api/client';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { Chip } from '../components/Chip';
import { ListItem } from '../components/ListItem';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

export default function MenuScreen() {
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [categoriaId, setCategoriaId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');

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
      // updater funcional: no necesitamos categoriaId como dependencia
      setCategoriaId((actual) => (actual === null && cats.length > 0 ? cats[0].id : actual));
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
    setAviso('');
    try {
      // DELETE /productos/{id} responde 200 {eliminado, mensaje}: si el
      // producto tiene historial de pedidos NO se borra, se desactiva
      // (api/app/routers/productos.py). Sin mostrar `mensaje` el usuario cree
      // que borró algo que sigue ahí.
      const resultado = await deleteProducto(id);
      setAviso(resultado.mensaje);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el producto');
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Gestión de Menú</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {aviso ? <Text style={styles.aviso}>{aviso}</Text> : null}

      <Input placeholder="Nombre" value={nombre} onChangeText={setNombre} />
      <Input placeholder="Precio" value={precio} onChangeText={setPrecio} keyboardType="numeric" />
      <Input placeholder="Descripción" value={descripcion} onChangeText={setDescripcion} />

      <View style={styles.categorias}>
        {categorias.map((cat) => (
          <Chip
            key={cat.id}
            label={cat.nombre}
            selected={categoriaId === cat.id}
            onPress={() => setCategoriaId(cat.id)}
          />
        ))}
      </View>

      <Button variant="secondary" label="Agregar producto" onPress={agregarProducto} />

      <FlatList
        data={productos}
        keyExtractor={(item) => item.id.toString()}
        style={styles.list}
        ListEmptyComponent={<EmptyState icon="restaurant-outline" message="Sin productos registrados." />}
        renderItem={({ item }) => (
          <ListItem
            title={item.nombre}
            subtitle={`$${item.precio_venta} · ${item.categoria.nombre}`}
            trailing={
              <TouchableOpacity style={styles.iconBtn} onPress={() => eliminar(item.id)}>
                <Ionicons name="trash-outline" size={22} color={colors.danger} />
              </TouchableOpacity>
            }
          />
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  error: { color: colors.danger, marginBottom: spacing.md },
  aviso: { color: colors.info, marginBottom: spacing.md },
  categorias: { flexDirection: 'row', flexWrap: 'wrap' },
  list: { marginTop: spacing.md },
  iconBtn: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
});
