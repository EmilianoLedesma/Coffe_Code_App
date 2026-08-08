import { request } from './client';

export function crearCompra({ ingredienteId, cantidad, monto }) {
  return request('/compras', {
    method: 'POST',
    body: {
      ingrediente_id: ingredienteId,
      cantidad,
      monto,
    },
  });
}
