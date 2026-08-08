import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  KeyboardAvoidingView,
  ScrollView,
  Platform
} from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { ApiError } from '../api/client';
import { colors, typography, spacing } from '../theme';
import { Card } from '../components/Card';
import { Input } from '../components/Input';
import { Button } from '../components/Button';

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

        <Card size="hero" style={styles.card}>

          <Input
            placeholder="correo electrónico"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
          />

          <Input
            placeholder="contraseña"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Button
            variant="primary"
            label={loading ? 'Ingresando...' : 'Iniciar sesión'}
            onPress={handleLogin}
            disabled={loading}
          />

          <Button
            variant="text"
            label="¿Olvidaste tu contraseña?"
            onPress={() => navigation.navigate('RecuperarPassword')}
          />

        </Card>

      </ScrollView>

    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({

  container: {
    flexGrow: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },

  logo: {
    width: 270,
    height: 270,
    marginBottom: spacing.sm,
  },

  title: {
    fontSize: typography.size.hero,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
  },

  subtitle: {
    fontSize: typography.size.xl,
    color: colors.textSecondary,
    marginBottom: spacing.xxl,
  },

  card: {
    width: '100%',
  },

  error: {
    color: colors.danger,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
});
