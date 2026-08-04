import { request } from './client';

export function getPedidosListos() {
  return request('/pedidos?estado=Listo');
}

export function getPedido(pedidoId) {
  return request(`/pedidos/${pedidoId}`);
}
