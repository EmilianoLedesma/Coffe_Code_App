import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  Image,
  KeyboardAvoidingView,
  ScrollView,
  Platform
} from 'react-native';

export default function LoginScreen({ navigation }) {

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rol, setRol] = useState('mesero');

  const login = () => {

    // 🔥 1. campos vacíos
    if (!email.trim() || !password.trim()) {
      alert('Faltan campos');
      return;
    }

    // 🔥 2. correo válido
    if (!email.includes('@')) {
      alert('Correo inválido');
      return;
    }

    // 🔥 3. contraseña mínima
    if (password.length < 4) {
      alert('Contraseña muy corta');
      return;
    }

    // ✔ éxito
    alert(`Bienvenido ${rol}`);

    navigation.replace('Home');
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >

      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >

        <Image
          source={require('../assets/logo3.png')}
          style={styles.logo}
          resizeMode="contain"
        />

        <Text style={styles.title}>Coffee Code</Text>
        <Text style={styles.subtitle}>Sistema de cafetería</Text>

        <View style={styles.card}>

          <TextInput
            placeholder="correo electrónico"
            value={email}
            onChangeText={setEmail}
            style={styles.input}
          />

          <TextInput
            placeholder="contraseña"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            style={styles.input}
          />

          <Text style={styles.label}>rol: {rol}</Text>

          <View style={styles.roles}>
            <TouchableOpacity onPress={() => setRol('mesero')}>
              <Text style={rol === 'mesero' ? styles.selected : styles.role}>
                mesero
              </Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={() => setRol('cocina')}>
              <Text style={rol === 'cocina' ? styles.selected : styles.role}>
                cocina
              </Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={() => setRol('caja')}>
              <Text style={rol === 'caja' ? styles.selected : styles.role}>
                caja
              </Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.button} onPress={login}>
            <Text style={styles.buttonText}>Iniciar sesión</Text>
          </TouchableOpacity>

        </View>

      </ScrollView>

    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({

  container: {
    flexGrow: 1,
    backgroundColor: '#F5F5F5',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },

  logo: {
    width: 270,
    height: 270,
    marginBottom: 10,
  },

  title: {
    fontSize: 30,
    fontWeight: 'bold',
    color: '#2E1B0F',
  },

  subtitle: {
    fontSize: 16,
    color: 'gray',
    marginBottom: 20,
  },

  card: {
    width: '100%',
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 15,
    elevation: 6,
  },

  input: {
    borderWidth: 1,
    borderColor: '#E0E0E0',
    backgroundColor: '#FAFAFA',
    padding: 12,
    marginBottom: 10,
    borderRadius: 10,
  },

  label: {
    marginTop: 10,
    fontWeight: 'bold',
    color: '#2E1B0F',
  },

  roles: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 15,
  },

  role: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    color: 'gray',
  },

  selected: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#2E1B0F',
    color: 'white',
  },

  button: {
    backgroundColor: '#2E1B0F',
    padding: 14,
    borderRadius: 10,
    marginTop: 10,
  },

  buttonText: {
    color: 'white',
    textAlign: 'center',
    fontWeight: 'bold',
  },
});