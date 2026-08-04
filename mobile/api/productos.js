import { request } from './client';

export function getProductos() {
  return request('/productos');
}

export function createProducto({ nombre, descripcion, precioVenta, idCategoria }) {
  return request('/productos', {
    method: 'POST',
    body: {
      nombre,
      descripcion: descripcion || null,
      precio_venta: precioVenta,
      disponible: true,
      activo: true,
      id_categoria: idCategoria,
    },
  });
}

export function updateProducto(id, payload) {
  return request(`/productos/${id}`, { method: 'PUT', body: payload });
}

export function deleteProducto(id) {
  return request(`/productos/${id}`, { method: 'DELETE' });
}
