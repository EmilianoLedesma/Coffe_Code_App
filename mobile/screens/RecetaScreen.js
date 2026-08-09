import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import {
  getRecetasPorProducto,
  crearReceta,
  actualizarReceta,
  eliminarReceta,
  eliminarRecetaCompleta,
} from '../api/recetas';
import { getIngredientes } from '../api/ingredientes';
import { ApiError } from '../api/client';
import { Card } from '../components/Card';
import { Chip } from '../components/Chip';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { EmptyState } from '../components/EmptyState';
import { colors, typography, spacing } from '../theme';

export default function RecetaScreen({ route }) {
  const { productoId, productoNombre } = route.params;

  const [receta, setReceta] = useState([]);
  const [ingredientes, setIngredientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [ingredienteId, setIngredienteId] = useState(null);
  const [cantidad, setCantidad] = useState('');
  const [guardando, setGuardando] = useState(false);

  const [editandoId, setEditandoId] = useState(null);
  const [cantidadEditada, setCantidadEditada] = useState('');

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [recetaData, ingredientesData] = await Promise.all([
        getRecetasPorProducto(productoId),
        getIngredientes(),
      ]);
      setReceta(recetaData);
      setIngredientes(ingredientesData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
  }, [productoId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const agregarIngrediente = async () => {
    if (!ingredienteId || !cantidad) {
      setError('Selecciona un ingrediente e ingresa la cantidad');
      return;
    }

    setGuardando(true);
    setError('');
    try {
      await crearReceta({ productoId, ingredienteId, cantidad: parseFloat(cantidad) });
      setIngredienteId(null);
      setCantidad('');
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo agregar el ingrediente');
    } finally {
      setGuardando(false);
    }
  };

  const iniciarEdicion = (linea) => {
    setEditandoId(linea.id_ingrediente);
    setCantidadEditada(String(linea.cantidad_requerida));
  };

  const guardarEdicion = async (idIngrediente) => {
    setError('');
    try {
      await actualizarReceta(productoId, idIngrediente, parseFloat(cantidadEditada));
      setEditandoId(null);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo actualizar la cantidad');
    }
  };

  const eliminarLinea = async (idIngrediente) => {
    setError('');
    try {
      await eliminarReceta(productoId, idIngrediente);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el ingrediente');
    }
  };

  const confirmarEliminarTodo = () => {
    Alert.alert(
      'Eliminar receta completa',
      `Esto quita todos los ingredientes de ${productoNombre}. ¿Continuar?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Eliminar', style: 'destructive', onPress: eliminarTodo },
      ]
    );
  };

  const eliminarTodo = async () => {
    setError('');
    try {
      await eliminarRecetaCompleta(productoId);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar la receta');
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
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <FlatList
        data={receta}
        keyExtractor={(item) => item.id_ingrediente.toString()}
        style={styles.list}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <>
            <Text style={styles.title}>Receta: {productoNombre}</Text>
            {error ? <Text style={styles.error}>{error}</Text> : null}
          </>
        }
        ListEmptyComponent={<EmptyState icon="list-outline" message="Sin ingredientes en la receta aún." />}
        ListFooterComponent={
          <>
            <Text style={styles.subtitle}>Agregar ingrediente</Text>

            <View style={styles.chipsRow}>
              {ingredientes.map((ing) => (
                <Chip
                  key={ing.id}
                  label={ing.nombre}
                  selected={ingredienteId === ing.id}
                  onPress={() => setIngredienteId(ing.id)}
                />
              ))}
            </View>

            <Input
              placeholder="Cantidad requerida"
              value={cantidad}
              onChangeText={setCantidad}
              keyboardType="numeric"
            />

            <Button
              variant="secondary"
              label={guardando ? 'Guardando...' : 'Agregar'}
              onPress={agregarIngrediente}
              disabled={guardando}
            />

            <View style={styles.eliminarWrap}>
              <Button variant="text" label="Eliminar receta completa" onPress={confirmarEliminarTodo} />
            </View>
          </>
        }
        renderItem={({ item }) => (
          <Card style={styles.card}>
            <Text style={styles.name}>{item.ingrediente.nombre}</Text>

            {editandoId === item.id_ingrediente ? (
              <View style={styles.row}>
                <Input
                  style={{ flex: 1 }}
                  keyboardType="numeric"
                  value={cantidadEditada}
                  onChangeText={setCantidadEditada}
                />
                <Button variant="text" label="Guardar" onPress={() => guardarEdicion(item.id_ingrediente)} />
              </View>
            ) : (
              <>
                <Text style={styles.cantidad}>
                  Cantidad: {item.cantidad_requerida} {item.ingrediente.unidad}
                </Text>
                <View style={styles.row}>
                  <Button variant="text" label="Editar" onPress={() => iniciarEdicion(item)} />
                  <Button variant="text" label="Eliminar" onPress={() => eliminarLinea(item.id_ingrediente)} />
                </View>
              </>
            )}
          </Card>
        )}
      />
    </KeyboardAvoidingView>
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
  subtitle: {
    marginTop: spacing.md,
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  error: { color: colors.danger, marginBottom: spacing.md },
  list: { flex: 1, marginBottom: spacing.md },
  card: { marginBottom: spacing.sm },
  name: { fontSize: typography.size.lg, fontWeight: typography.weight.bold, color: colors.textPrimary },
  cantidad: { color: colors.textSecondary, marginTop: spacing.xs },
  row: { flexDirection: 'row', alignItems: 'center', marginTop: spacing.sm, gap: spacing.sm },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap' },
  eliminarWrap: { marginTop: spacing.sm },
});
