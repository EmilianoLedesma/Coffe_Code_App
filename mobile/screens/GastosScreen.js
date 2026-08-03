import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  Alert,
  StyleSheet
} from 'react-native';

export default function GastosScreen() {

  const [descripcion, setDescripcion] = useState('');
  const [monto, setMonto] = useState('');
  const [gastos, setGastos] = useState([]);

  const agregarGasto = () => {
    if (!descripcion || !monto) {
      Alert.alert('Error', 'Completa todos los campos');
      return;
    }

    const nuevo = {
      id: Date.now().toString(),
      descripcion,
      monto: parseFloat(monto)
    };

    setGastos([nuevo, ...gastos]);

    Alert.alert('Gasto registrado', `Se agregó: ${descripcion}`);

    setDescripcion('');
    setMonto('');
  };

  const eliminarGasto = (id) => {
    setGastos(gastos.filter(item => item.id !== id));

    Alert.alert('Eliminado', 'Gasto eliminado correctamente');
  };

  const total = gastos.reduce((acc, item) => acc + item.monto, 0);

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Caja - Gastos y Cuentas</Text>

      {/* INPUTS */}
      <View style={styles.card}>

        <TextInput
          placeholder="Descripción del gasto"
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

        <TouchableOpacity style={styles.btnAgregar} onPress={agregarGasto}>
          <Text style={styles.btnText}>Agregar gasto</Text>
        </TouchableOpacity>

      </View>

      {/* TOTAL */}
      <View style={styles.totalBox}>
        <Text style={styles.totalText}>Total gastos: ${total}</Text>
      </View>

      {/* LISTA */}
      <FlatList
        data={gastos}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.item}>

            <View>
              <Text style={styles.desc}>{item.descripcion}</Text>
              <Text style={styles.monto}>${item.monto}</Text>
            </View>

            <TouchableOpacity
              style={styles.deleteBtn}
              onPress={() => eliminarGasto(item.id)}
            >
              <Text style={{ color: 'white' }}>X</Text>
            </TouchableOpacity>

          </View>
        )}
      />

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    padding: 15
  },

  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 10
  },

  card: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10
  },

  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 10,
    marginBottom: 10
  },

  btnAgregar: {
    backgroundColor: '#2E1B0F',
    padding: 12,
    borderRadius: 8
  },

  btnText: {
    color: 'white',
    textAlign: 'center',
    fontWeight: 'bold'
  },

  totalBox: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10
  },

  totalText: {
    fontSize: 18,
    fontWeight: 'bold'
  },

  item: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },

  desc: {
    fontSize: 16,
    fontWeight: 'bold'
  },

  monto: {
    color: 'gray'
  },

  deleteBtn: {
    backgroundColor: 'red',
    padding: 10,
    borderRadius: 8
  }
});