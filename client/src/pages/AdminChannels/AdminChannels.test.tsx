// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import AdminChannels from './AdminChannels';

const mocks = vi.hoisted(() => ({
  copyChannelFolderTree: vi.fn(),
  createChannelFolder: vi.fn(),
  deleteChannelFolder: vi.fn(),
  fetchChannelFolderCatalog: vi.fn(),
  fetchImages: vi.fn(),
  renameChannelFolder: vi.fn(),
}));

vi.mock('@client/src/api/image', () => ({
  copyChannelFolderTree: mocks.copyChannelFolderTree,
  createChannelFolder: mocks.createChannelFolder,
  createManagedChannel: vi.fn(),
  deleteChannelFolder: mocks.deleteChannelFolder,
  fetchChannelFolderCatalog: mocks.fetchChannelFolderCatalog,
  fetchImages: mocks.fetchImages,
  renameChannelFolder: mocks.renameChannelFolder,
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
      { name: '官网大图', folders: [
        { id: 'landing', name: '课程介绍', parentId: null },
      ] },
    ]);
    mocks.fetchImages.mockReset().mockResolvedValue({
      items: [], hasMore: false, nextCursor: null,
    });
    mocks.copyChannelFolderTree.mockReset().mockResolvedValue({ created: 2, skipped: 0 });
  });

  afterEach(cleanup);

  it('copies the whole selected channel folder structure into another channel root', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <AdminChannels />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    const open = await screen.findByRole('button', { name: '复制“PPT”的分类结构' });
    expect(screen.getByText('复制当前渠道的完整分类，不会复制、移动或绑定图片。')).toBeTruthy();
    fireEvent.click(open);
    expect((screen.getByRole('combobox', { name: '分类结构目标渠道' }) as HTMLSelectElement).value)
      .toBe('官网大图');
    fireEvent.click(screen.getByRole('button', { name: '确认复制' }));

    await waitFor(() => {
      expect(mocks.copyChannelFolderTree).toHaveBeenCalledWith('PPT', '官网大图', null, null);
    });
  });

  it('copies a selected folder subtree into a selected target folder', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <AdminChannels />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await screen.findByRole('button', { name: '复制“PPT”的分类结构' });
    fireEvent.click(screen.getByRole('button', { name: '展开产品的下级分类' }));
    fireEvent.click(screen.getByRole('button', { name: 'AI功能' }));
    fireEvent.click(screen.getByRole('button', { name: '复制到' }));

    expect(screen.getByText('把“产品 / AI功能”复制到')).toBeTruthy();
    fireEvent.change(screen.getByRole('combobox', { name: '目标上级分类' }), {
      target: { value: 'landing' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认复制' }));

    await waitFor(() => {
      expect(mocks.copyChannelFolderTree).toHaveBeenCalledWith(
        'PPT',
        '官网大图',
        'ai',
        'landing',
      );
    });
  });
});
