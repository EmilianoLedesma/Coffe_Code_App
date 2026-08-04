import { request } from './client';

export function login(correo_electronico, password) {
  return request('/auth/login', {
    method: 'POST',
    body: { correo_electronico, password },
    auth: false,
  });
}
