import React, { useState } from 'react';
import { View, Text, StyleSheet, Alert, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { updateIngrediente, ajustarStock, deleteIngrediente } from '../api/ingredientes';
import { ApiError } from '../api/client';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { Chip } from '../components/Chip';
import { colors, typography, spacing } from '../theme';

const UNIDADES = ['g', 'ml', 'u', 'kg', 'l'];

export default function IngredienteDetalleScreen({ route, navigation }) {
  const { ingrediente } = route.params;

  const [nombre, setNombre] = useState(ingrediente.nombre);
  const [unidad, setUnidad] = useState(ingrediente.unidad);
  const [stockMinimo, setStockMinimo] = useState(String(ingrediente.stock_minimo));
  const [costoUnitario, setCostoUnitario] = useState(String(ingrediente.costo_unitario));
  const [stockActual, setStockActual] = useState(String(ingrediente.stock_actual));

  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);

  const guardar = async () => {
    if (!nombre.trim() || !unidad || !stockMinimo || !costoUnitario || !stockActual) {
      setError('Completa nombre, unidad, stock actual, stock mínimo y costo unitario');
      return;
    }

    const nuevoStock = parseFloat(stockActual);
    const delta = nuevoStock - Number(ingrediente.stock_actual);

    setGuardando(true);
    setError('');
    try {
      if (delta !== 0) {
        await ajustarStock(ingrediente.id, delta);
      }
      await updateIngrediente(ingrediente.id, {
        nombre: nombre.trim(),
        unidad,
        stockMinimo: parseFloat(stockMinimo),
        costoUnitario: parseFloat(costoUnitario),
      });
      navigation.goBack();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el ingrediente');
    } finally {
      setGuardando(false);
    }
  };

  const confirmarEliminar = () => {
    Alert.alert(
      'Eliminar ingrediente',
      `¿Eliminar "${ingrediente.nombre}"? Si está en uso en alguna receta se desactivará en vez de borrarse.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Eliminar', style: 'destructive', onPress: eliminar },
      ]
    );
  };

  const eliminar = async () => {
    setError('');
    try {
      const resultado = await deleteIngrediente(ingrediente.id);
      Alert.alert('Listo', resultado.mensaje, [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el ingrediente');
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        style={styles.container}
        contentContainerStyle={{ paddingBottom: spacing.xxl }}
        keyboardShouldPersistTaps="handled"
      >
      <Text style={styles.title}>Editar ingrediente</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Text style={styles.label}>Nombre</Text>
      <Input placeholder="Nombre" value={nombre} onChangeText={setNombre} />

      <Text style={styles.label}>Unidad</Text>
      <View style={styles.chipsRow}>
        {UNIDADES.map((u) => (
          <Chip key={u} label={u} selected={unidad === u} onPress={() => setUnidad(u)} />
        ))}
      </View>

      <Text style={styles.label}>Stock actual</Text>
      <Input
        placeholder="Stock actual"
        value={stockActual}
        onChangeText={setStockActual}
        keyboardType="numeric"
      />

      <Text style={styles.label}>Stock mínimo</Text>
      <Input
        placeholder="Stock mínimo"
        value={stockMinimo}
        onChangeText={setStockMinimo}
        keyboardType="numeric"
      />

      <Text style={styles.label}>Costo unitario</Text>
      <Input
        placeholder="Costo unitario"
        value={costoUnitario}
        onChangeText={setCostoUnitario}
        keyboardType="numeric"
      />

      <Button
        variant="secondary"
        label={guardando ? 'Guardando...' : 'Guardar cambios'}
        onPress={guardar}
        disabled={guardando}
      />

      <View style={styles.eliminarWrap}>
        <Button variant="text" label="Eliminar ingrediente" onPress={confirmarEliminar} />
      </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { flex: 1, padding: spacing.lg, backgroundColor: colors.background },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  label: { color: colors.textSecondary, marginBottom: spacing.xs, fontSize: typography.size.md },
  error: { color: colors.danger, marginBottom: spacing.md },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing.sm },
  eliminarWrap: { marginTop: spacing.md },
});
