// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import AdminAnnouncements from './AdminAnnouncements';

const mocks = vi.hoisted(() => ({
  fetchManagedAnnouncements: vi.fn(),
  publishAnnouncement: vi.fn(),
}));

vi.mock('@client/src/api/announcements', () => ({
  fetchManagedAnnouncements: mocks.fetchManagedAnnouncements,
  publishAnnouncement: mocks.publishAnnouncement,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe('AdminAnnouncements', () => {
  it('publishes a trimmed announcement for all business users', async () => {
    mocks.fetchManagedAnnouncements.mockResolvedValue({ items: [] });
    mocks.publishAnnouncement.mockResolvedValue({
      id: 'notice-1',
      title: '今日更新',
      content: '增加消息中心',
      publisherName: 'designer',
      publishedAt: '2026-09-13T12:00:00Z',
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <AdminAnnouncements />
      </QueryClientProvider>,
    );

    fireEvent.change(screen.getByPlaceholderText('例如：今日新增批量上传功能'), {
      target: { value: '  今日更新  ' },
    });
    fireEvent.change(screen.getByPlaceholderText(/写清楚今天优化了什么/), {
      target: { value: '  增加消息中心  ' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发布给所有业务用户' }));

    await waitFor(() => {
      expect(mocks.publishAnnouncement).toHaveBeenCalledWith({
        title: '今日更新',
        content: '增加消息中心',
      });
    });
  });
});
