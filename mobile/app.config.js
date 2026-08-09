export default {
  expo: {
    name: 'coffeecodemovil',
    slug: 'coffeecodemovil',
    version: '1.0.0',
    orientation: 'portrait',
    plugins: ['expo-secure-store'],
    extra: {
      // Sin valor por defecto a proposito: config.js deriva la IP LAN en
      // runtime desde el hostUri que Expo ya usa para conectar el
      // dispositivo, asi no hay que hardcodear ni actualizar la IP cada
      // vez que cambia la red. Esta variable solo sirve para forzar un
      // override manual (ej. build de produccion contra un dominio fijo).
      apiUrl: process.env.API_URL || null,
    },
  },
};
