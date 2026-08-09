import Constants from 'expo-constants';

const API_PORT = '8010';
const FALLBACK_API_URL = 'http://192.168.100.31:8010';

function resolveApiUrl() {
  const override = Constants.expoConfig?.extra?.apiUrl;
  if (override) return override;

  // hostUri es el mismo host:puerto que el celular ya usa para conectarse
  // al bundler de Expo — deriva la IP LAN actual sin hardcodearla, evita
  // que cambie de red/router rompa la conexion al API.
  const hostUri = Constants.expoConfig?.hostUri || Constants.expoGoConfig?.debuggerHost;
  if (hostUri) {
    const host = hostUri.split(':')[0];
    return `http://${host}:${API_PORT}`;
  }

  return FALLBACK_API_URL;
}

export const API_URL = resolveApiUrl();
export const WS_URL = API_URL.replace(/^http/, 'ws');
