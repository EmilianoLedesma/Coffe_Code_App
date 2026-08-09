import React, { useCallback, useState } from 'react';
import { View, Text, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { getProductos, createProducto, updateProducto, deleteProducto } from '../api/productos';
import { getCategorias } from '../api/categorias';
import { ApiError } from '../api/client';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { Chip } from '../components/Chip';
import { ListItem } from '../components/ListItem';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

export default function MenuScreen({ navigation }) {
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [categoriaId, setCategoriaId] = useState(null);
  const [categoriaFiltro, setCategoriaFiltro] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');

  const [nombre, setNombre] = useState('');
  const [precio, setPrecio] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [disponible, setDisponible] = useState(true);
  const [editandoId, setEditandoId] = useState(null);

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

  const limpiarFormulario = () => {
    setNombre('');
    setPrecio('');
    setDescripcion('');
    setDisponible(true);
    setEditandoId(null);
  };

  const iniciarEdicion = (producto) => {
    setEditandoId(producto.id);
    setNombre(producto.nombre);
    setPrecio(String(producto.precio_venta));
    setDescripcion(producto.descripcion || '');
    setDisponible(producto.disponible);
    setCategoriaId(producto.categoria.id);
  };

  const guardarProducto = async () => {
    if (!nombre.trim() || !precio || !categoriaId) {
      setError('Completa nombre, precio y categoría');
      return;
    }

    setError('');
    try {
      if (editandoId) {
        await updateProducto(editandoId, {
          nombre: nombre.trim(),
          descripcion: descripcion.trim() || null,
          precio_venta: parseFloat(precio),
          disponible,
          id_categoria: categoriaId,
        });
      } else {
        await createProducto({
          nombre: nombre.trim(),
          descripcion: descripcion.trim(),
          precioVenta: parseFloat(precio),
          idCategoria: categoriaId,
        });
      }
      limpiarFormulario();
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el producto');
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

  const productosVisibles = categoriaFiltro
    ? productos.filter((p) => p.categoria.id === categoriaFiltro)
    : productos;

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Gestión de Menú</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {aviso ? <Text style={styles.aviso}>{aviso}</Text> : null}

      <Text style={styles.label}>Filtrar por categoría</Text>
      <View style={styles.categorias}>
        <Chip label="Todas" selected={categoriaFiltro === null} onPress={() => setCategoriaFiltro(null)} />
        {categorias.map((cat) => (
          <Chip
            key={cat.id}
            label={cat.nombre}
            selected={categoriaFiltro === cat.id}
            onPress={() => setCategoriaFiltro(cat.id)}
          />
        ))}
      </View>

      <Text style={styles.subtitle}>{editandoId ? 'Editar producto' : 'Agregar producto'}</Text>

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

      {editandoId ? (
        <View style={styles.categorias}>
          <Chip label="Disponible" selected={disponible} onPress={() => setDisponible(true)} />
          <Chip label="No disponible" selected={!disponible} onPress={() => setDisponible(false)} />
        </View>
      ) : null}

      <View style={styles.formBotones}>
        <Button
          variant="secondary"
          label={editandoId ? 'Guardar cambios' : 'Agregar producto'}
          onPress={guardarProducto}
        />
        {editandoId ? (
          <Button variant="text" label="Cancelar" onPress={limpiarFormulario} />
        ) : null}
      </View>

      <FlatList
        data={productosVisibles}
        keyExtractor={(item) => item.id.toString()}
        style={styles.list}
        ListEmptyComponent={<EmptyState icon="restaurant-outline" message="Sin productos registrados." />}
        renderItem={({ item }) => (
          <ListItem
            title={item.nombre}
            subtitle={`$${item.precio_venta} · ${item.categoria.nombre}`}
            trailing={
              <View style={styles.acciones}>
                <TouchableOpacity style={styles.iconBtn} onPress={() => iniciarEdicion(item)}>
                  <Ionicons name="create-outline" size={22} color={colors.primary} />
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.iconBtn}
                  onPress={() => navigation.navigate('Receta', { productoId: item.id, productoNombre: item.nombre })}
                >
                  <Ionicons name="list-outline" size={22} color={colors.primary} />
                </TouchableOpacity>

                <TouchableOpacity style={styles.iconBtn} onPress={() => eliminar(item.id)}>
                  <Ionicons name="trash-outline" size={22} color={colors.danger} />
                </TouchableOpacity>
              </View>
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
  label: { color: colors.textSecondary, marginBottom: spacing.xs, fontSize: typography.size.md },
  subtitle: {
    marginTop: spacing.md,
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  error: { color: colors.danger, marginBottom: spacing.md },
  aviso: { color: colors.info, marginBottom: spacing.md },
  categorias: { flexDirection: 'row', flexWrap: 'wrap' },
  formBotones: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  list: { marginTop: spacing.md },
  acciones: { flexDirection: 'row' },
  iconBtn: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
});
