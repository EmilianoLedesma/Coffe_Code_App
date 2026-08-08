jest.mock('../config', () => ({ API_URL: 'http://test.local' }));
jest.mock('../auth/session', () => ({
  getToken: jest.fn(() => Promise.resolve('fake-token')),
  clearToken: jest.fn(() => Promise.resolve()),
}));

import { getPedidoActivoDeMesa } from './pedidos';

function jsonResponse(body) {
  return {
    ok: true,
    status: 200,
    text: () => Promise.resolve(JSON.stringify(body)),
  };
}

const PEDIDO_MESA_3 = { id: 10, id_mesa: 3, id_estatus: 1 };

beforeEach(() => {
  global.fetch = jest.fn((url) => {
    if (url.includes('estado=Pendiente')) return Promise.resolve(jsonResponse([PEDIDO_MESA_3]));
    if (url.includes('estado=En%20preparaci%C3%B3n')) return Promise.resolve(jsonResponse([]));
    if (url.includes('estado=Listo')) return Promise.resolve(jsonResponse([]));
    return Promise.resolve(jsonResponse([]));
  });
});

afterEach(() => jest.clearAllMocks());

describe('getPedidoActivoDeMesa', () => {
  it('filters by id_mesa and returns the matching pedido', async () => {
    const pedido = await getPedidoActivoDeMesa(3);
    expect(pedido).toEqual(PEDIDO_MESA_3);
    expect(global.fetch).toHaveBeenCalledTimes(3);
  });

  it('returns falsy when there is no active pedido for that mesa', async () => {
    const pedido = await getPedidoActivoDeMesa(99);
    expect(pedido).toBeFalsy();
  });
});
