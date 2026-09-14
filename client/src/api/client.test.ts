// @vitest-environment jsdom

import { AxiosError, type AxiosResponse } from 'axios';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api, AUTH_EXPIRED_EVENT } from './client';

describe('API authentication expiry handling', () => {
  const onExpired = vi.fn();

  afterEach(() => {
    window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
    onExpired.mockReset();
  });

  it('announces a protected 401 so stale image queries cannot look like empty channels', async () => {
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);

    await expect(api.get('/api/images', {
      adapter: async (config) => {
        const response: AxiosResponse = {
          data: { code: 'unauthorized' },
          status: 401,
          statusText: 'Unauthorized',
          headers: {},
          config,
        };
        throw new AxiosError(
          'Unauthorized',
          'ERR_BAD_REQUEST',
          config,
          undefined,
          response,
        );
      },
    })).rejects.toBeInstanceOf(AxiosError);

    expect(onExpired).toHaveBeenCalledOnce();
  });
});
