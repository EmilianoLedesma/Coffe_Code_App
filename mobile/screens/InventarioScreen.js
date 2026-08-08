import React, { useCallback, useState } from 'react';
import { View, Text, TouchableOpacity, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { getIngredientes, createIngrediente, ajustarStock, deleteIngrediente } from '../api/ingredientes';
import { ApiError } from '../api/client';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { ListItem } from '../components/ListItem';
import { Badge } from '../components/Badge';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

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
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Inventario</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {aviso ? <Text style={styles.aviso}>{aviso}</Text> : null}

      <Input placeholder="Nombre" value={nombre} onChangeText={setNombre} />
      <Input placeholder="Unidad (g, ml, u)" value={unidad} onChangeText={setUnidad} />
      <Input placeholder="Stock mínimo" value={stockMinimo} onChangeText={setStockMinimo} keyboardType="numeric" />
      <Input placeholder="Costo unitario" value={costoUnitario} onChangeText={setCostoUnitario} keyboardType="numeric" />

      <Button variant="secondary" label="Agregar ingrediente" onPress={agregar} />

      <FlatList
        data={items}
        keyExtractor={(i) => i.id.toString()}
        style={styles.list}
        ListEmptyComponent={<EmptyState icon="cube-outline" message="Sin ingredientes registrados." />}
        renderItem={({ item }) => {
          const bajoMinimo = Number(item.stock_actual) < Number(item.stock_minimo);
          return (
            <ListItem
              title={item.nombre}
              subtitle={`Stock: ${item.stock_actual} ${item.unidad} · Mínimo: ${item.stock_minimo} ${item.unidad}`}
              trailing={
                <View style={styles.trailing}>
                  {bajoMinimo ? <Badge label="Bajo mínimo" tone="danger" /> : null}

                  <View style={styles.acciones}>
                    <TouchableOpacity style={styles.iconBtn} onPress={() => subir(item.id)}>
                      <Ionicons name="add-circle-outline" size={24} color={colors.success} />
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.iconBtn} onPress={() => bajar(item.id)}>
                      <Ionicons name="remove-circle-outline" size={24} color={colors.warning} />
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.iconBtn} onPress={() => eliminar(item.id)}>
                      <Ionicons name="trash-outline" size={22} color={colors.danger} />
                    </TouchableOpacity>
                  </View>
                </View>
              }
            />
          );
        }}
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
  list: { marginTop: spacing.md },
  trailing: { alignItems: 'flex-end' },
  acciones: { flexDirection: 'row', marginTop: spacing.xs },
  iconBtn: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
});
