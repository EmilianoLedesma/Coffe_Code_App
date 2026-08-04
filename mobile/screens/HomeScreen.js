import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useAuth } from '../auth/AuthContext';

const BOTONES_POR_ROL = {
  Mesero: [{ label: 'Mesero', target: 'Mesas' }],
  Cocinero: [{ label: 'Cocina', target: 'Cocina' }],
  Cajero: [{ label: 'Caja', target: 'Caja' }],
  Administrador: [
    { label: 'Mesero', target: 'Mesas' },
    { label: 'Cocina', target: 'Cocina' },
    { label: 'Caja', target: 'Caja' },
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
        <TouchableOpacity
          key={boton.target}
          style={styles.button}
          onPress={() => navigation.navigate(boton.target)}
        >
          <Text style={styles.text}>{boton.label}</Text>
        </TouchableOpacity>
      ))}

      <TouchableOpacity style={styles.logout} onPress={handleLogout}>
        <Text style={styles.logoutText}>Cerrar sesión</Text>
      </TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    justifyContent: 'center',
    padding: 20
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 5
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 30,
    color: 'gray'
  },
  button: {
    backgroundColor: '#2E1B0F',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15
  },
  text: {
    color: 'white',
    fontSize: 18,
    textAlign: 'center'
  },
  logout: {
    marginTop: 20,
    padding: 10,
  },
  logoutText: {
    color: '#C0392B',
    textAlign: 'center',
  },
});
