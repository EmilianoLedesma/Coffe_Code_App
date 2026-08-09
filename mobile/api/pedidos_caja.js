import { request } from './client';

export function getPedido(pedidoId) {
  return request(`/pedidos/${pedidoId}`);
}
