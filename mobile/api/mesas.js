import { request } from './client';

export function getMesas() {
  return request('/mesas');
}
