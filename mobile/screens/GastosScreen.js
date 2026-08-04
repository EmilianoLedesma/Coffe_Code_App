import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { crearGasto } from '../api/gastos';
import { getResumenCaja } from '../api/caja';
import { ApiError } from '../api/client';

export default function GastosScreen() {

  const [descripcion, setDescripcion] = useState('');
  const [monto, setMonto] = useState('');
  const [gastosSesion, setGastosSesion] = useState([]);
  const [totalPeriodo, setTotalPeriodo] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

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

  useFocusEffect(
    useCallback(() => {
      cargarResumen();
    }, [cargarResumen])
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
      setGastosSesion([creado, ...gastosSesion]);
      setDescripcion('');
      setMonto('');
      await cargarResumen();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo registrar el gasto');
    } finally {
      setGuardando(false);
    }
  };

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Caja - Gastos y Cuentas</Text>

      <View style={styles.card}>

        <TextInput
          placeholder="Descripción del gasto (mín. 3 caracteres)"
          value={descripcion}
          onChangeText={setDescripcion}
          style={styles.input}
        />

        <TextInput
          placeholder="Monto"
          value={monto}
          onChangeText={setMonto}
          keyboardType="numeric"
          style={styles.input}
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TouchableOpacity style={styles.btnAgregar} onPress={agregarGasto} disabled={guardando}>
          <Text style={styles.btnText}>{guardando ? 'Guardando...' : 'Agregar gasto'}</Text>
        </TouchableOpacity>

      </View>

      <View style={styles.totalBox}>
        <Text style={styles.totalText}>
          Total gastos de hoy (servidor): {totalPeriodo !== null ? `$${totalPeriodo}` : 'no disponible'}
        </Text>
      </View>

      <FlatList
        data={gastosSesion}
        keyExtractor={(item) => item.id.toString()}
        ListHeaderComponent={gastosSesion.length > 0 ? <Text style={{ marginBottom: 5, color: 'gray' }}>Registrados en esta sesión:</Text> : null}
        renderItem={({ item }) => (
          <View style={styles.item}>
            <View>
              <Text style={styles.desc}>{item.concepto}</Text>
              <Text style={styles.monto}>${item.monto}</Text>
            </View>
          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({

  container: { flex: 1, backgroundColor: '#F5F5F5', padding: 15 },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  card: { backgroundColor: 'white', padding: 15, borderRadius: 10, marginBottom: 10 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 10, marginBottom: 10 },
  error: { color: '#C0392B', marginBottom: 10 },
  btnAgregar: { backgroundColor: '#2E1B0F', padding: 12, borderRadius: 8 },
  btnText: { color: 'white', textAlign: 'center', fontWeight: 'bold' },
  totalBox: { backgroundColor: '#fff', padding: 15, borderRadius: 10, marginBottom: 10 },
  totalText: { fontSize: 16, fontWeight: 'bold' },
  item: { backgroundColor: 'white', padding: 15, borderRadius: 10, marginBottom: 10 },
  desc: { fontSize: 16, fontWeight: 'bold' },
  monto: { color: 'gray' },
});
