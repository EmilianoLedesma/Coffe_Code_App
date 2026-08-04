import { request } from './client';

export function getProductos() {
  return request('/productos');
}
