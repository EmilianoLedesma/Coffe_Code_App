export default {
  expo: {
    name: 'coffeecodemovil',
    slug: 'coffeecodemovil',
    version: '1.0.0',
    orientation: 'portrait',
    plugins: ['expo-secure-store'],
    extra: {
      apiUrl: process.env.API_URL || 'http://192.168.100.31:8010',
    },
  },
};
