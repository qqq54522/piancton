// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import AdminChannels from './AdminChannels';

const mocks = vi.hoisted(() => ({
  copyChannelFolderTree: vi.fn(),
  fetchChannelFolderCatalog: vi.fn(),
  fetchImages: vi.fn(),
}));

vi.mock('@client/src/api/image', () => ({
  copyChannelFolderTree: mocks.copyChannelFolderTree,
  createManagedChannel: vi.fn(),
  fetchChannelFolderCatalog: mocks.fetchChannelFolderCatalog,
  fetchImages: mocks.fetchImages,
}));

vi.mock('@client/src/pages/ImageHome/channelIntentCatalog', () => ({
  addChannelIntentEntry: vi.fn(),
  useChannelIntentEntries: () => [
    { value: 'PPT', label: 'PPT' },
    { value: '官网大图', label: '官网大图' },
  ],
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe('AdminChannels folder copy tool', () => {
  beforeEach(() => {
    mocks.fetchChannelFolderCatalog.mockReset().mockResolvedValue([
      { name: 'PPT', folders: [
        { id: 'product', name: '产品', parentId: null },
        { id: 'ai', name: 'AI功能', parentId: 'product' },
      ] },
      { name: '官网大图', folders: [] },
    ]);
    mocks.fetchImages.mockReset().mockResolvedValue({
      items: [], hasMore: false, nextCursor: null,
    });
    mocks.copyChannelFolderTree.mockReset().mockResolvedValue({ created: 2, skipped: 0 });
  });

  afterEach(cleanup);

  it('copies only the selected channel folder structure into another channel', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <AdminChannels />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    const open = await screen.findByRole('button', { name: '复制“PPT”的分类结构' });
    expect(screen.getByText('只复制目录层级，不会复制、移动或绑定任何图片。')).toBeTruthy();
    fireEvent.click(open);
    expect((screen.getByRole('combobox', { name: '分类结构目标渠道' }) as HTMLSelectElement).value)
      .toBe('官网大图');
    fireEvent.click(screen.getByRole('button', { name: '确认复制' }));

    await waitFor(() => {
      expect(mocks.copyChannelFolderTree).toHaveBeenCalledWith('PPT', '官网大图');
    });
  });
});
