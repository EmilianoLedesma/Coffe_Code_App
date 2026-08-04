export default {
  expo: {
    name: 'coffeecodemovil',
    slug: 'coffeecodemovil',
    version: '1.0.0',
    orientation: 'portrait',
    plugins: ['expo-secure-store'],
    extra: {
      apiUrl: process.env.API_URL || 'http://10.16.72.248:8000',
    },
  },
};
