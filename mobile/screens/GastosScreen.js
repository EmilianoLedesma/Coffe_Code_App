import React, { useCallback, useState } from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { crearGasto } from '../api/gastos';
import { getResumenCaja } from '../api/caja';
import { ApiError } from '../api/client';
import { getIngredientes } from '../api/ingredientes';
import { crearCompra } from '../api/compras';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Chip } from '../components/Chip';
import { Input } from '../components/Input';
import { ListItem } from '../components/ListItem';
import { colors, typography, spacing, radii } from '../theme';

export default function GastosScreen() {

  const [descripcion, setDescripcion] = useState('');
  const [monto, setMonto] = useState('');
  const [gastosSesion, setGastosSesion] = useState([]);
  const [totalPeriodo, setTotalPeriodo] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  const [ingredientes, setIngredientes] = useState([]);
  const [ingredienteId, setIngredienteId] = useState(null);
  const [cantidadCompra, setCantidadCompra] = useState('');
  const [comprando, setComprando] = useState(false);
  const [resultadoCompra, setResultadoCompra] = useState(null);
  const [errorCompra, setErrorCompra] = useState('');

  const cargarResumen = useCallback(async () => {
    try {
      const hoy = new Date();
      const desde = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()).toISOString();
      const resumen = await getResumenCaja(desde);
      setTotalPeriodo(resumen.total_gastos);
    } catch (err) {
      // el resumen es informativo; si falla no bloquea el registro de gastos
      setTotalPeriodo(null);
    }
  }, []);

  const cargarIngredientes = useCallback(async () => {
    try {
      setIngredientes(await getIngredientes());
    } catch (err) {
      setIngredientes([]);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargarResumen();
      cargarIngredientes();
    }, [cargarResumen, cargarIngredientes])
  );

  const agregarGasto = async () => {
    if (!descripcion.trim() || !monto) {
      setError('Completa todos los campos');
      return;
    }

    setGuardando(true);
    setError('');
    try {
      const creado = await crearGasto({ concepto: descripcion.trim(), monto: parseFloat(monto) });
      // updater funcional: evita perder un gasto si dos altas caen seguidas
      // sobre el mismo `gastosSesion` capturado en el closure.
      setGastosSesion((actual) => [creado, ...actual]);
      setDescripcion('');
      setMonto('');
      await cargarResumen();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el gasto');
    } finally {
      setGuardando(false);
    }
  };

  const registrarCompra = async () => {
    if (!ingredienteId || !cantidadCompra) {
      setErrorCompra('Selecciona un ingrediente y completa la cantidad');
      return;
    }

    setComprando(true);
    setErrorCompra('');
    setResultadoCompra(null);
    try {
      const ingrediente = ingredientes.find((i) => i.id === ingredienteId);
      const monto = parseFloat(cantidadCompra) * Number(ingrediente.costo_unitario);
      const resultado = await crearCompra({
        ingredienteId,
        cantidad: parseFloat(cantidadCompra),
        monto,
      });
      setResultadoCompra(resultado);
      setCantidadCompra('');
      await cargarResumen();
    } catch (err) {
      setErrorCompra(err instanceof ApiError ? err.message : 'No se pudo registrar la compra');
    } finally {
      setComprando(false);
    }
  };

  const renderHeader = () => (
    <>

      <Text style={styles.title}>Caja - Gastos y Cuentas</Text>

      <Card style={styles.card}>

        <Input
          placeholder="Descripción del gasto (mín. 3 caracteres)"
          value={descripcion}
          onChangeText={setDescripcion}
        />

        <Input
          placeholder="Monto"
          value={monto}
          onChangeText={setMonto}
          keyboardType="numeric"
        />

        {error ? (
          <View style={styles.errorBanner}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        <Button
          variant="primary"
          label={guardando ? 'Guardando...' : 'Agregar gasto'}
          onPress={agregarGasto}
          loading={guardando}
          disabled={guardando}
        />

      </Card>

      <Card style={styles.card}>

        <Text style={styles.cardHeading}>Comprar insumo</Text>

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
          placeholder="Cantidad"
          value={cantidadCompra}
          onChangeText={setCantidadCompra}
          keyboardType="numeric"
        />

        {ingredienteId && cantidadCompra ? (
          <Text style={styles.montoCalculado}>
            Monto: $
            {(
              parseFloat(cantidadCompra) *
              Number(ingredientes.find((i) => i.id === ingredienteId)?.costo_unitario || 0)
            ).toFixed(2)}
          </Text>
        ) : null}

        {resultadoCompra ? (
          <Text style={styles.successText}>
            Compra registrada. Nuevo stock: {resultadoCompra.nuevo_stock}
          </Text>
        ) : null}

        {errorCompra ? (
          <View style={styles.errorBanner}>
            <Text style={styles.errorText}>{errorCompra}</Text>
          </View>
        ) : null}

        <Button
          variant="primary"
          label={comprando ? 'Registrando...' : 'Registrar compra'}
          onPress={registrarCompra}
          loading={comprando}
          disabled={comprando}
        />

      </Card>

      <Card style={styles.card}>
        <Text style={styles.totalText}>
          Total gastos de hoy (servidor): {totalPeriodo !== null ? `$${totalPeriodo}` : 'no disponible'}
        </Text>
      </Card>

      {gastosSesion.length > 0 ? (
        <Text style={styles.sesionLabel}>Registrados en esta sesión:</Text>
      ) : null}

    </>
  );

  return (
    <View style={styles.container}>

      <FlatList
        data={gastosSesion}
        keyExtractor={(item) => item.id.toString()}
        ListHeaderComponent={renderHeader}
        renderItem={({ item }) => (
          <ListItem title={item.concepto} subtitle={`$${item.monto}`} />
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({

  container: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  card: { marginBottom: spacing.md },
  cardHeading: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  errorBanner: {
    backgroundColor: colors.dangerTint,
    borderWidth: 1,
    borderColor: 'rgba(192,57,43,0.3)',
    borderRadius: radii.r8,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  errorText: { color: colors.danger, fontSize: typography.size.md },
  successText: { color: colors.success, marginBottom: spacing.md, fontSize: typography.size.md },
  montoCalculado: { color: colors.textPrimary, fontWeight: typography.weight.semibold, marginBottom: spacing.md },
  totalText: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
  },
  sesionLabel: { marginBottom: spacing.sm, color: colors.textSecondary },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap' },
});
