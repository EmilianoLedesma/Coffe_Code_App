import { request } from './client';

export function getIngredientes() {
  return request('/ingredientes');
}

export function createIngrediente({ nombre, unidad, stockMinimo, costoUnitario, stockInicial }) {
  return request('/ingredientes', {
    method: 'POST',
    body: {
      nombre,
      unidad,
      stock_actual: stockInicial || 0,
      stock_minimo: stockMinimo,
      costo_unitario: costoUnitario,
      activo: true,
    },
  });
}

export function ajustarStock(id, cantidad) {
  return request(`/ingredientes/${id}/stock`, {
    method: 'PUT',
    body: { cantidad },
  });
}

export function deleteIngrediente(id) {
  return request(`/ingredientes/${id}`, { method: 'DELETE' });
}
