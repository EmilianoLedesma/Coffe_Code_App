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

// GET /pedidos no filtra por mesa; se piden los tres estados activos y se
// filtra client-side. Mesero tiene permiso de lectura sobre GET /pedidos
// (api/app/routers/pedidos.py:39-49). Devuelve el más avanzado (preferencia:
// Listo > En preparación > Pendiente) o null.
export async function getPedidoActivoDeMesa(mesaId) {
  const listas = await Promise.all(
    ESTADOS_ACTIVOS.map((estado) => request(`/pedidos?estado=${encodeURIComponent(estado)}&limit=200`))
  );
  const activos = listas.flat().filter((p) => p.id_mesa === mesaId);
  return activos.length ? activos[activos.length - 1] : null;
}
