import { request } from './client';

// Estados en los que un pedido sigue "vivo" — espejo de
// ESTATUS_PEDIDO_ACTIVOS en api/app/core/constants.py:43-47
const ESTADOS_ACTIVOS = ['Pendiente', 'En preparación', 'Listo'];

export function crearPedido({ mesaId, usuarioId, items }) {
  return request('/pedidos', {
    method: 'POST',
    body: {
      mesa_id: mesaId,
      usuario_id: usuarioId,
      items: items.map((item) => ({
        id_producto: item.id_producto,
        cantidad: item.cantidad,
        especificaciones: item.especificaciones || null,
      })),
    },
  });
}

export function getPedido(pedidoId) {
  return request(`/pedidos/${pedidoId}`);
}

export function cambiarEstadoPedido(pedidoId, estatus) {
  return request(`/pedidos/${pedidoId}/estado`, {
    method: 'PUT',
    body: { estatus },
  });
}

// GET /pedidos?mesa_id= trae TODOS los pedidos de la mesa (cualquier
// estatus); se filtra client-side a los activos para no listar pedidos ya
// Entregados/Cancelados como si siguieran vivos.
export async function getPedidosActivosDeMesa(mesaId) {
  const todos = await request(`/pedidos?mesa_id=${mesaId}&limit=200`);
  return todos.filter((p) => ESTADOS_ACTIVOS.includes(p.estatus.nombre));
}

export function agregarItemPedido(pedidoId, { idProducto, cantidad, especificaciones }) {
  return request(`/pedidos/${pedidoId}/items`, {
    method: 'POST',
    body: { id_producto: idProducto, cantidad, especificaciones: especificaciones || null },
  });
}

export function actualizarItemPedido(pedidoId, itemId, { cantidad, especificaciones }) {
  const body = {};
  if (cantidad !== undefined) body.cantidad = cantidad;
  if (especificaciones !== undefined) body.especificaciones = especificaciones;
  return request(`/pedidos/${pedidoId}/items/${itemId}`, { method: 'PUT', body });
}

export function eliminarItemPedido(pedidoId, itemId) {
  return request(`/pedidos/${pedidoId}/items/${itemId}`, { method: 'DELETE' });
}

export function cerrarCuenta(pedidoId) {
  return request(`/pedidos/${pedidoId}/cerrar-cuenta`, { method: 'POST' });
}
