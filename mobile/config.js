import Constants from 'expo-constants';

export const API_URL = Constants.expoConfig.extra.apiUrl;
export const WS_URL = API_URL.replace(/^http/, 'ws');
