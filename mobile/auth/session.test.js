import { decodeToken } from './session';

function base64url(str) {
  return Buffer.from(str)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

function makeJwt(payload) {
  const header = base64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = base64url(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

describe('decodeToken', () => {
  it('decodes a valid JWT payload', () => {
    const payload = { rol: 'Mesero', user_id: 1, exp: 9999999999 };
    const token = makeJwt(payload);
    expect(decodeToken(token)).toEqual(payload);
  });

  it('returns {} for malformed/garbage input without throwing', () => {
    expect(() => decodeToken('not-a-jwt')).not.toThrow();
    expect(decodeToken('not-a-jwt')).toEqual({});
    expect(decodeToken('')).toEqual({});
    expect(decodeToken('a.b.c')).toEqual({});
  });

  it('decodes a payload whose base64url segment requires padding', () => {
    // Payload chosen so its base64url body length % 4 !== 0, exercising the padding fix.
    const payload = { rol: 'Cocinero', user_id: 1, exp: 9999999999 };
    const token = makeJwt(payload);
    const rawBody = token.split('.')[1];
    expect(rawBody.length % 4).not.toBe(0);
    expect(decodeToken(token)).toEqual(payload);
  });
});
