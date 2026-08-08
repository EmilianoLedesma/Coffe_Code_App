import React, { createContext, useContext, useEffect, useState } from 'react';
import { getToken, saveToken, clearToken, decodeToken } from './session';
import { login as loginRequest } from '../api/auth';
import { setUnauthorizedHandler } from '../api/client';
import { navigationRef } from '../navigationRef';

const AuthContext = createContext(null);
const SIN_SESION = { token: null, rol: null, userId: null, loading: false };

export function AuthProvider({ children }) {
  const [session, setSession] = useState({ ...SIN_SESION, loading: true });

  useEffect(() => {
    (async () => {
      const token = await getToken();
      const payload = token ? decodeToken(token) : null;
      // token presente pero vencido == sin sesión; no esperamos al primer 401
      const vigente = payload && payload.exp && payload.exp * 1000 > Date.now();
      if (vigente) {
        setSession({ token, rol: payload.rol, userId: payload.user_id, loading: false });
      } else {
        if (token) await clearToken();
        setSession(SIN_SESION);
      }
    })();
  }, []);

  useEffect(() => {
    // client.js avisa aquí en cualquier 401: limpiamos estado y volvemos a Login.
    setUnauthorizedHandler(async () => {
      await clearToken();
      setSession(SIN_SESION);
      if (navigationRef.isReady()) {
        navigationRef.resetRoot({ index: 0, routes: [{ name: 'Login' }] });
      }
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const login = async (correo, password) => {
    const { access_token, rol } = await loginRequest(correo, password);
    await saveToken(access_token);
    const payload = decodeToken(access_token);
    setSession({ token: access_token, rol, userId: payload.user_id, loading: false });
    return rol;
  };

  const logout = async () => {
    await clearToken();
    setSession(SIN_SESION);
  };

  return (
    <AuthContext.Provider value={{ ...session, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
