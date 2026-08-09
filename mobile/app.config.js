export default {
  expo: {
    name: 'coffeecodemovil',
    slug: 'coffeecodemovil',
    version: '1.0.0',
    orientation: 'portrait',
    plugins: ['expo-secure-store'],
    extra: {
      // La clave se omite del todo si no hay override: Expo serializa
      // `null` como `{}` en el manifest de `extra`, así que dejarla en
      // `null` rompe el chequeo de config.js (un objeto vacío es truthy).
      // Sin esta clave, config.js deriva la IP LAN en runtime desde el
      // hostUri que Expo ya usa para conectar el dispositivo.
      ...(process.env.API_URL ? { apiUrl: process.env.API_URL } : {}),
    },
  },
};
