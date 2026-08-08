import React, { useState } from 'react';
import { View, Text, StyleSheet, Alert } from 'react-native';
import { colors, typography, spacing } from '../theme';
import { Card } from '../components/Card';
import { Input } from '../components/Input';
import { Button } from '../components/Button';

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

      <Card size="hero">

        <Input
          placeholder="Correo electrónico"
          value={email}
          onChangeText={setEmail}
        />

        <Button variant="primary" label="Enviar enlace" onPress={enviar} />

        <Button variant="text" label="← Volver al login" onPress={() => navigation.goBack()} />

      </Card>

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: spacing.xl,
    backgroundColor: colors.background
  },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.sm
  },
  subtitle: {
    marginBottom: spacing.xxl,
    color: colors.textSecondary
  },
});
