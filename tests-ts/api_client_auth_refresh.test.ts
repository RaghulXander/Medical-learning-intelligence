import { afterEach, describe, expect, test } from 'bun:test';
import { MedicalApiClient } from '../packages/api-client/src/client';

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe('MedicalApiClient access-token refresh', () => {
  test('refreshes once and retries an authenticated request after a 401', async () => {
    let token = 'expired-token';
    let refreshCalls = 0;
    const authorizationHeaders: string[] = [];

    globalThis.fetch = (async (_input, init) => {
      const authorization = new Headers(init?.headers).get('Authorization') ?? '';
      authorizationHeaders.push(authorization);
      if (authorization === 'Bearer expired-token') {
        return new Response(JSON.stringify({ detail: 'Invalid access token' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return Response.json({ saved: true });
    }) as typeof fetch;

    const client = new MedicalApiClient({
      baseUrl: 'https://example.test',
      getToken: () => token,
      onUnauthorized: async () => {
        refreshCalls += 1;
        token = 'fresh-token';
        return token;
      },
    });

    await expect(
      client.request('/api/admin/retrieval-review/case-1', {
        method: 'PATCH',
        body: JSON.stringify({ notes: 'reviewed' }),
      })
    ).resolves.toEqual({ saved: true });
    expect(refreshCalls).toBe(1);
    expect(authorizationHeaders).toEqual([
      'Bearer expired-token',
      'Bearer fresh-token',
    ]);
  });

  test('does not retry forever when the refreshed token is rejected', async () => {
    let token = 'expired-token';
    let fetchCalls = 0;
    let refreshCalls = 0;

    globalThis.fetch = (async () => {
      fetchCalls += 1;
      return new Response(JSON.stringify({ detail: 'Invalid access token' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }) as typeof fetch;

    const client = new MedicalApiClient({
      baseUrl: 'https://example.test',
      getToken: () => token,
      onUnauthorized: () => {
        refreshCalls += 1;
        token = 'also-invalid';
        return token;
      },
    });

    await expect(client.request('/api/admin/retrieval-review/case-1')).rejects.toMatchObject({
      status: 401,
      message: 'Invalid access token',
    });
    expect(fetchCalls).toBe(2);
    expect(refreshCalls).toBe(1);
  });
});
