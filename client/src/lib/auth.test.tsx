// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { AUTH_EXPIRED_EVENT } from '@client/src/api/client';
import { AuthProvider, useAuth } from './auth';

const mocks = vi.hoisted(() => ({
  me: vi.fn(),
}));

vi.mock('@client/src/api/auth', () => ({
  me: mocks.me,
  login: vi.fn(),
  logout: vi.fn(),
  completeOnboarding: vi.fn(),
}));

describe('AuthProvider expired sessions', () => {
  it('clears stale server data and removes the cached user on a protected 401', async () => {
    mocks.me.mockResolvedValue({ id: 'user-1', username: 'business', role: 'business' });
    const queryClient = new QueryClient();
    queryClient.setQueryData(['images'], { items: [{ id: 'cached-image' }] });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider><CurrentUser /></AuthProvider>
      </QueryClientProvider>,
    );

    await screen.findByText('business');
    act(() => window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT)));

    await waitFor(() => expect(screen.getByText('signed-out')).toBeTruthy());
    expect(queryClient.getQueryData(['images'])).toBeUndefined();
  });
});

function CurrentUser() {
  const { user } = useAuth();
  return <span>{user?.username ?? 'signed-out'}</span>;
}
