// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import MyMessages from './MyMessages';

const mocks = vi.hoisted(() => ({
  fetchAnnouncements: vi.fn(),
  markAnnouncementsRead: vi.fn(),
}));

vi.mock('@client/src/api/announcements', () => ({
  fetchAnnouncements: mocks.fetchAnnouncements,
  markAnnouncementsRead: mocks.markAnnouncementsRead,
}));

describe('MyMessages', () => {
  it('marks the newest visible announcement read when the page opens', async () => {
    mocks.fetchAnnouncements.mockResolvedValue({
      unreadCount: 2,
      items: [
        {
          id: 'newest',
          title: '新增批量上传',
          content: '现在可以一次选择多张主图。',
          publisherName: 'designer',
          publishedAt: '2026-09-13T12:00:00Z',
        },
        {
          id: 'older',
          title: '旧公告',
          content: '旧内容',
          publisherName: 'admin',
          publishedAt: '2026-09-12T12:00:00Z',
        },
      ],
    });
    mocks.markAnnouncementsRead.mockResolvedValue({ unreadCount: 0 });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter><MyMessages /></MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText('新增批量上传')).toBeTruthy();
    await waitFor(() => {
      expect(mocks.markAnnouncementsRead).toHaveBeenCalledTimes(1);
      expect(mocks.markAnnouncementsRead).toHaveBeenCalledWith('2026-09-13T12:00:00Z');
    });
  });
});
