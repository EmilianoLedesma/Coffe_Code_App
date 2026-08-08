import React, { useEffect } from 'react';
import { View, Text, StyleSheet, Image, ActivityIndicator } from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { colors, typography, spacing } from '../theme';

export default function SplashScreen({ navigation }) {
  const { token, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    navigation.replace(token ? 'Home' : 'Login');
  }, [loading, token, navigation]);


    return (
        <View style={styles.container}>

        <Image
            source={require('../assets/logo3.png')} // ajusta la ruta
            style={styles.logo}
            resizeMode="contain"
        />



        <ActivityIndicator
            size="large"
            color={colors.primary}
            style={{ marginTop: spacing.xl }}
        />

        <Text style={styles.loadingText}>Cargando...</Text>

        </View>
);

}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center'
  },
  logo: {
    width: 350,
    height: 350,
    marginBottom: spacing.lg
  },

  loadingText: {
    marginTop: spacing.md,
    color: colors.textPrimary,
    fontSize: typography.size.xxl
  }
});
