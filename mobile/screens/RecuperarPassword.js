import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';

export default function RecuperarPassword({ navigation }) {

  const [email, setEmail] = useState('');

  const enviar = () => {
    if (!email) {
      Alert.alert('Error', 'Ingresa tu correo');
      return;
    }

    Alert.alert(
      'Recuperación enviada',
      'Revisa tu correo para restablecer tu contraseña'
    );

    navigation.goBack(); // regresa al login
  };

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Recuperar contraseña</Text>

      <Text style={styles.subtitle}>
        Ingresa tu correo para enviarte un enlace de recuperación
      </Text>

      <TextInput
        placeholder="Correo electrónico"
        style={styles.input}
        value={email}
        onChangeText={setEmail}
      />

      <TouchableOpacity style={styles.button} onPress={enviar}>
        <Text style={{ color: 'white' }}>Enviar enlace</Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={() => navigation.goBack()}>
        <Text style={styles.back}>← Volver al login</Text>
      </TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: '#F5F5F5'
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10
  },
  subtitle: {
    marginBottom: 20,
    color: '#555'
  },
  input: {
    borderWidth: 1,
    padding: 12,
    borderRadius: 8,
    marginBottom: 15,
    backgroundColor: 'white'
  },
  button: {
    backgroundColor: '#2E1B0F',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center'
  },
  back: {
    marginTop: 15,
    textAlign: 'center',
    color: '#2E1B0F',
    fontWeight: 'bold'
  }
});