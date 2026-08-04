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
import { useAuth } from '../auth/AuthContext';
import { ApiError } from '../api/client';

export default function LoginScreen({ navigation }) {

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleLogin = async () => {
    setError('');

    if (!email.trim() || !password.trim()) {
      setError('Faltan campos');
      return;
    }

    if (!email.includes('@')) {
      setError('Correo inválido');
      return;
    }

    setLoading(true);
    try {
      await login(email.trim(), password);
      navigation.replace('Home');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo conectar con el servidor');
    } finally {
      setLoading(false);
    }
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
            autoCapitalize="none"
            style={styles.input}
          />

          <TextInput
            placeholder="contraseña"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            style={styles.input}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
            <Text style={styles.buttonText}>{loading ? 'Ingresando...' : 'Iniciar sesión'}</Text>
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

  error: {
    color: '#C0392B',
    marginBottom: 10,
    textAlign: 'center',
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
