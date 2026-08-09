import { request } from './client';

export function getRecetasPorProducto(productoId) {
  return request(`/producto_ingrediente?producto_id=${productoId}`);
}

export function crearReceta({ productoId, ingredienteId, cantidad }) {
  return request('/producto_ingrediente', {
    method: 'POST',
    body: {
      producto_id: productoId,
      ingrediente_id: ingredienteId,
      cantidad,
    },
  });
}

export function actualizarReceta(productoId, ingredienteId, cantidad) {
  return request(`/producto_ingrediente/${productoId}/${ingredienteId}`, {
    method: 'PUT',
    body: { cantidad },
  });
}

export function eliminarReceta(productoId, ingredienteId) {
  return request(`/producto_ingrediente/${productoId}/${ingredienteId}`, { method: 'DELETE' });
}

export function eliminarRecetaCompleta(productoId) {
  return request(`/producto_ingrediente/producto/${productoId}`, { method: 'DELETE' });
}
