import React, { createContext, useContext, useEffect, useState } from 'react';
import { getToken, saveToken, clearToken, decodeToken } from './session';
import { login as loginRequest } from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState({ token: null, rol: null, userId: null, loading: true });

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (token) {
        const payload = decodeToken(token);
        setSession({ token, rol: payload.rol, userId: payload.user_id, loading: false });
      } else {
        setSession({ token: null, rol: null, userId: null, loading: false });
      }
    })();
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
    setSession({ token: null, rol: null, userId: null, loading: false });
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
