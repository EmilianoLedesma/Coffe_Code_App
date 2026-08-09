jest.mock('../config', () => ({ API_URL: 'http://test.local' }));
jest.mock('../auth/session', () => ({
  getToken: jest.fn(() => Promise.resolve('fake-token')),
  clearToken: jest.fn(() => Promise.resolve()),
}));

import { getPedidosActivosDeMesa, agregarItemPedido, actualizarItemPedido, eliminarItemPedido, cerrarCuenta } from './pedidos';

function jsonResponse(body) {
  return {
    ok: true,
    status: 200,
    text: () => Promise.resolve(JSON.stringify(body)),
  };
}

const PEDIDO_PENDIENTE = { id: 10, id_mesa: 3, estatus: { nombre: 'Pendiente' }, ocupa_mesa: true };
const PEDIDO_ENTREGADO = { id: 11, id_mesa: 3, estatus: { nombre: 'Entregado' }, ocupa_mesa: false };

beforeEach(() => {
  global.fetch = jest.fn((url) => {
    if (url.includes('mesa_id=3')) return Promise.resolve(jsonResponse([PEDIDO_PENDIENTE, PEDIDO_ENTREGADO]));
    if (url.includes('mesa_id=99')) return Promise.resolve(jsonResponse([]));
    return Promise.resolve(jsonResponse({ id: 10 }));
  });
});

afterEach(() => jest.clearAllMocks());

describe('getPedidosActivosDeMesa', () => {
  it('filtra por ocupa_mesa (excluye Entregado ya pagado/Cancelado)', async () => {
    const activos = await getPedidosActivosDeMesa(3);
    expect(activos).toEqual([PEDIDO_PENDIENTE]);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it('devuelve lista vacía cuando la mesa no tiene pedidos', async () => {
    const activos = await getPedidosActivosDeMesa(99);
    expect(activos).toEqual([]);
  });
});

describe('agregarItemPedido', () => {
  it('manda POST a /pedidos/{id}/items con el shape correcto', async () => {
    await agregarItemPedido(10, { idProducto: 5, cantidad: 2, especificaciones: 'Sin azúcar' });
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toContain('/pedidos/10/items');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({ id_producto: 5, cantidad: 2, especificaciones: 'Sin azúcar' });
  });
});

describe('actualizarItemPedido', () => {
  it('manda PUT a /pedidos/{id}/items/{itemId}', async () => {
    await actualizarItemPedido(10, 7, { cantidad: 3 });
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toContain('/pedidos/10/items/7');
    expect(options.method).toBe('PUT');
    expect(JSON.parse(options.body)).toEqual({ cantidad: 3 });
  });
});

describe('eliminarItemPedido', () => {
  it('manda DELETE a /pedidos/{id}/items/{itemId}', async () => {
    await eliminarItemPedido(10, 7);
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toContain('/pedidos/10/items/7');
    expect(options.method).toBe('DELETE');
  });
});

describe('cerrarCuenta', () => {
  it('manda POST a /pedidos/{id}/cerrar-cuenta', async () => {
    await cerrarCuenta(10);
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toContain('/pedidos/10/cerrar-cuenta');
    expect(options.method).toBe('POST');
  });
});
