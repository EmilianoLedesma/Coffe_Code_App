import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { colors, typography, spacing } from '../theme';
import { ListItem } from '../components/ListItem';
import { Button } from '../components/Button';

const BOTONES_POR_ROL = {
  Mesero: [{ label: 'Mesero', target: 'Mesas', icon: 'restaurant-outline' }],
  Cocinero: [{ label: 'Cocina', target: 'Cocina', icon: 'flame-outline' }],
  Cajero: [{ label: 'Caja', target: 'Caja', icon: 'cash-outline' }],
  Administrador: [
    { label: 'Mesero', target: 'Mesas', icon: 'restaurant-outline' },
    { label: 'Cocina', target: 'Cocina', icon: 'flame-outline' },
    { label: 'Caja', target: 'Caja', icon: 'cash-outline' },
  ],
};

export default function HomeScreen({ navigation }) {
  const { rol, logout } = useAuth();
  const botones = BOTONES_POR_ROL[rol] || [];

  const handleLogout = async () => {
    await logout();
    navigation.replace('Login');
  };

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Coffee Code</Text>
      <Text style={styles.subtitle}>Panel principal ({rol})</Text>

      {botones.map((boton) => (
        <ListItem
          key={boton.target}
          icon={boton.icon}
          title={boton.label}
          onPress={() => navigation.navigate(boton.target)}
        />
      ))}

      <View style={styles.logout}>
        <Button variant="secondary" label="Cerrar sesión" onPress={handleLogout} />
      </View>

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    padding: spacing.xl
  },
  title: {
    fontSize: typography.size.hero,
    fontWeight: typography.weight.bold,
    textAlign: 'center',
    color: colors.textPrimary,
    marginBottom: spacing.xs
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: spacing.xxxl,
    color: colors.textSecondary
  },
  logout: {
    marginTop: spacing.xl,
  },
});
