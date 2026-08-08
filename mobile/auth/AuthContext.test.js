import React from 'react';
import { Text } from 'react-native';
import { render, renderHook, waitFor } from '@testing-library/react-native';

jest.mock('../config', () => ({ API_URL: 'http://test.local' }));

jest.mock('./session', () => ({
  ...jest.requireActual('./session'),
  getToken: jest.fn(),
  saveToken: jest.fn(() => Promise.resolve()),
  clearToken: jest.fn(() => Promise.resolve()),
}));

import { getToken, clearToken } from './session';
import { AuthProvider, useAuth } from './AuthContext';

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

afterEach(() => jest.clearAllMocks());

describe('AuthProvider restore on mount', () => {
  it('clears an expired token instead of restoring a session', async () => {
    const expiredToken = makeJwt({ rol: 'Mesero', user_id: 1, exp: 1 }); // exp: 1970, long expired
    getToken.mockResolvedValue(expiredToken);

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(clearToken).toHaveBeenCalledTimes(1);
    expect(result.current.token).toBeNull();
    expect(result.current.rol).toBeNull();
  });

  it('does not clear/reject a token that is still valid', async () => {
    const validToken = makeJwt({ rol: 'Cajero', user_id: 7, exp: 9999999999 });
    getToken.mockResolvedValue(validToken);

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(clearToken).not.toHaveBeenCalled();
    expect(result.current.token).toBe(validToken);
    expect(result.current.rol).toBe('Cajero');
  });
});

describe('AuthProvider happy path', () => {
  it('renders children and exposes token/rol via useAuth with no stored session', async () => {
    getToken.mockResolvedValue(null);

    const { getByText } = render(
      <AuthProvider>
        <Text>hijo renderizado</Text>
      </AuthProvider>
    );
    expect(getByText('hijo renderizado')).toBeTruthy();

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.token).toBeNull();
    expect(result.current.rol).toBeNull();
    expect(typeof result.current.login).toBe('function');
    expect(typeof result.current.logout).toBe('function');
  });
});
