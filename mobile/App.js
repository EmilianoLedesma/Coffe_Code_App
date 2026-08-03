import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import SplashScreen from './screens/SplashScreen';
import LoginScreen from './screens/LoginScreen';
import HomeScreen from './screens/HomeScreen';
import MesasScreen from './screens/MesasScreen';
import PedidoScreen from './screens/PedidoScreen';
import EstadoPedidoScreen from './screens/EstadoPedidoScreen';
import ColaPedidosScreen from './screens/ColaPedidosScreen';
import CajaScreen from './screens/CajaScreen';
import PagoScreen from './screens/PagoScreen';
import GastosScreen from './screens/GastosScreen';
import MenuScreen from './screens/MenuScreen';
import InventarioScreen from './screens/InventarioScreen';
import RecuperarPassword from './screens/RecuperarPassword';
import CocinaScreen from './screens/CocinaScreen';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Splash">

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
          name="EstadoPedido" 
          component={EstadoPedidoScreen} 
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

      </Stack.Navigator>
    </NavigationContainer>
  );
}