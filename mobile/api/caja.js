import { request } from './client';

export function registrarVenta({ ticketId, metodoPago, monto }) {
  return request('/ventas', {
    method: 'POST',
    body: { ticket_id: ticketId, metodo_pago: metodoPago, monto },
  });
}

export function getResumenCaja(desde, hasta) {
  const params = new URLSearchParams();
  if (desde) params.append('desde', desde);
  if (hasta) params.append('hasta', hasta);
  const query = params.toString();
  return request(`/caja/resumen${query ? `?${query}` : ''}`);
}
