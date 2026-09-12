// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import AdminUsers from './AdminUsers';

const mocks = vi.hoisted(() => ({ fetchUsers: vi.fn() }));

vi.mock('@client/src/api/admin', () => ({
  fetchUsers: mocks.fetchUsers,
  createUser: vi.fn(),
  updateUser: vi.fn(),
  resetPassword: vi.fn(),
}));

describe('AdminUsers', () => {
  it('shows every user identity code with an explicit copy action', async () => {
    mocks.fetchUsers.mockResolvedValue([
      {
        id: '72ed5fc2-3d8c-4652-ad3c-b053d6b6ffd4',
        username: 'codex_local_preview',
        role: 'admin',
        isActive: true,
        createdAt: '2026-09-12T00:00:00Z',
      },
    ]);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <MemoryRouter><AdminUsers /></MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText('72ed5fc2-3d8c-4652-ad3c-b053d6b6ffd4')).toBeTruthy();
    expect(screen.getByRole('button', { name: '复制 codex_local_preview 的用户身份码' })).toBeTruthy();
  });
});
