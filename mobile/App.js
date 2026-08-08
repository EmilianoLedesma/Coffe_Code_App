import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { colors, typography } from './theme';

import SplashScreen from './screens/SplashScreen';
import LoginScreen from './screens/LoginScreen';
import HomeScreen from './screens/HomeScreen';
import MesasScreen from './screens/MesasScreen';
import PedidoScreen from './screens/PedidoScreen';
import DetalleScreen from './screens/DetalleScreen';
import ColaPedidosScreen from './screens/ColaPedidosScreen';
import CajaScreen from './screens/CajaScreen';
import PagoScreen from './screens/PagoScreen';
import GastosScreen from './screens/GastosScreen';
import MenuScreen from './screens/MenuScreen';
import InventarioScreen from './screens/InventarioScreen';
import RecuperarPassword from './screens/RecuperarPassword';
import CocinaScreen from './screens/CocinaScreen';
import CocinaDetalleScreen from './screens/CocinaDetalleScreen';
import { AuthProvider } from './auth/AuthContext';
import { navigationRef } from './navigationRef';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer ref={navigationRef}>
        <Stack.Navigator
          initialRouteName="Splash"
          screenOptions={{
            headerStyle: { backgroundColor: colors.surface },
            headerTitleStyle: {
              color: colors.textPrimary,
              fontWeight: typography.weight.bold,
              fontSize: typography.size.xl,
            },
            headerTintColor: colors.primary,
            headerShadowVisible: false,
            contentStyle: { backgroundColor: colors.background },
          }}
        >

        <Stack.Screen
          name="Splash"
          component={SplashScreen}
          options={{ headerShown: false }}
        />

        <Stack.Screen
          name="Login"
          component={LoginScreen}
          options={{ headerShown: false }}
        />

        <Stack.Screen 
          name="Home" 
          component={HomeScreen} 
        />

        <Stack.Screen 
          name="Mesas" 
          component={MesasScreen} 
        />

        <Stack.Screen 
          name="Pedido" 
          component={PedidoScreen} 
        />

        

        <Stack.Screen
          name="Detalle"
          component={DetalleScreen}
        />

        <Stack.Screen 
          name="ColaPedidos" 
          component={ColaPedidosScreen} 
        />

        <Stack.Screen 
          name="Caja" 
          component={CajaScreen} 
        />

        <Stack.Screen 
          name="Pago" 
          component={PagoScreen}
        />

        <Stack.Screen 
          name="Gastos" 
          component={GastosScreen} 
        />

        <Stack.Screen 
          name="Menu" 
          component={MenuScreen} 
        />

        <Stack.Screen 
          name="Inventario" 
          component={InventarioScreen} 
        />

        <Stack.Screen 
          name="RecuperarPassword" 
          component={RecuperarPassword} 
        />

        <Stack.Screen
          name="Cocina"
          component={CocinaScreen}
        />

        <Stack.Screen
          name="CocinaDetalle"
          component={CocinaDetalleScreen}
        />

      </Stack.Navigator>
      </NavigationContainer>
    </AuthProvider>
  );
}