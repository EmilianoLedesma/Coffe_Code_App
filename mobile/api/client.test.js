jest.mock('../config', () => ({ API_URL: 'http://test.local' }));
jest.mock('../auth/session', () => ({
  getToken: jest.fn(() => Promise.resolve('fake-token')),
  clearToken: jest.fn(() => Promise.resolve()),
}));

import { request, setUnauthorizedHandler, ApiError } from './client';
import { clearToken } from '../auth/session';

function mockFetchOnce({ status = 200, body = null, json = true }) {
  global.fetch = jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(json ? JSON.stringify(body) : body),
  });
}

afterEach(() => {
  jest.clearAllMocks();
  setUnauthorizedHandler(null);
});

describe('mensajeDeError (via request error paths)', () => {
  it('joins array detail .msg fields with "; "', async () => {
    mockFetchOnce({
      status: 422,
      body: { detail: [{ msg: 'campo requerido' }, { msg: 'valor inválido' }] },
    });
    await expect(request('/algo')).rejects.toThrow('campo requerido; valor inválido');
  });

  it('passes through a string detail', async () => {
    mockFetchOnce({ status: 400, body: { detail: 'Credenciales inválidas' } });
    await expect(request('/algo')).rejects.toThrow('Credenciales inválidas');
  });

  it('falls back to "Error {status}" when detail is missing/null', async () => {
    mockFetchOnce({ status: 500, body: { detail: null } });
    await expect(request('/algo')).rejects.toThrow('Error 500');
  });

  it('falls back to "Error {status}" when body has no detail at all', async () => {
    mockFetchOnce({ status: 404, body: {} });
    await expect(request('/algo')).rejects.toThrow('Error 404');
  });
});

describe('request() 401 handling', () => {
  it('calls the registered setUnauthorizedHandler on a 401', async () => {
    mockFetchOnce({ status: 401, body: { detail: 'No autorizado' } });
    const handler = jest.fn();
    setUnauthorizedHandler(handler);

    await expect(request('/protegido')).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(clearToken).toHaveBeenCalledTimes(1);
  });

  it('does not call the handler for non-401 errors', async () => {
    mockFetchOnce({ status: 400, body: { detail: 'Bad request' } });
    const handler = jest.fn();
    setUnauthorizedHandler(handler);

    await expect(request('/algo')).rejects.toBeInstanceOf(ApiError);
    expect(handler).not.toHaveBeenCalled();
  });
});

describe('request() non-JSON response body', () => {
  it('does not throw when the body is not valid JSON', async () => {
    mockFetchOnce({ status: 200, body: 'not json {{{', json: false });
    await expect(request('/algo')).resolves.toBeNull();
  });

  it('falls back to a generic error message on a non-JSON error body', async () => {
    mockFetchOnce({ status: 502, body: '<html>Bad Gateway</html>', json: false });
    await expect(request('/algo')).rejects.toThrow('Error 502');
  });
});
