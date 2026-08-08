jest.mock('../config', () => ({ API_URL: 'http://test.local' }));
jest.mock('../auth/session', () => ({
  getToken: jest.fn(() => Promise.resolve('fake-token')),
  clearToken: jest.fn(() => Promise.resolve()),
}));

import { getTickets } from './tickets';

function jsonResponse(body) {
  return { ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(body)) };
}

beforeEach(() => {
  global.fetch = jest.fn(() => Promise.resolve(jsonResponse([])));
});

afterEach(() => jest.clearAllMocks());

describe('getTickets', () => {
  it('sin filtro pide /tickets sin query', async () => {
    await getTickets();
    expect(global.fetch.mock.calls[0][0]).toContain('/tickets');
    expect(global.fetch.mock.calls[0][0]).not.toContain('?');
  });

  it('con pagado:false agrega el query param', async () => {
    await getTickets({ pagado: false });
    expect(global.fetch.mock.calls[0][0]).toContain('/tickets?pagado=false');
  });
});
