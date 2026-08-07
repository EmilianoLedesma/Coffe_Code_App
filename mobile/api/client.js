import { API_URL } from '../config';
import { getToken, clearToken } from '../auth/session';

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// AuthContext registra aquí su forceLogout. client.js no importa React ni
// React Navigation: solo guarda un callback opcional.
let onUnauthorized = null;

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

function mensajeDeError(data, status) {
  const detail = data && data.detail;
  // FastAPI 422: detail es [{msg, loc, type}, ...], no un string.
  if (Array.isArray(detail)) {
    const msgs = detail.map((e) => e && e.msg).filter(Boolean);
    return msgs.length ? msgs.join('; ') : `Error ${status}`;
  }
  if (typeof detail === 'string' && detail) return detail;
  return `Error ${status}`;
}

export async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };

  if (auth) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (networkError) {
    throw new ApiError(0, 'Sin conexión con el servidor');
  }

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null; // respuesta no-JSON (proxy/502): cae al mensaje genérico
  }

  if (!response.ok) {
    if (response.status === 401 && auth) {
      await clearToken();
      if (onUnauthorized) onUnauthorized();
    }
    throw new ApiError(response.status, mensajeDeError(data, response.status));
  }

  return data;
}
