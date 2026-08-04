import { request } from './client';

export function crearGasto({ concepto, monto }) {
  return request('/gastos', {
    method: 'POST',
    body: { concepto, monto },
  });
}
