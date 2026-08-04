import { request } from './client';

export function getCategorias() {
  return request('/categorias');
}
