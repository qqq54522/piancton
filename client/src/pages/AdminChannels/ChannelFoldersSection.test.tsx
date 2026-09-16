// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ChannelFolderTree, ChannelImagesPane } from './ChannelFoldersSection';

const mocks = vi.hoisted(() => ({
  assignChannelFolder: vi.fn(),
  createChannelFolder: vi.fn(),
  deleteChannelFolder: vi.fn(),
  fetchImages: vi.fn(),
  renameChannelFolder: vi.fn(),
}));

vi.mock('@client/src/api/image', () => ({
  assignChannelFolder: mocks.assignChannelFolder,
  createChannelFolder: mocks.createChannelFolder,
  deleteChannelFolder: mocks.deleteChannelFolder,
  fetchImages: mocks.fetchImages,
  renameChannelFolder: mocks.renameChannelFolder,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const folders = [
  { id: 'folder-beijing', name: '北京', parentId: null },
  { id: 'folder-shanghai', name: '上海', parentId: null },
];

describe('ChannelImagesPane', () => {
  beforeEach(() => {
    mocks.fetchImages.mockReset().mockResolvedValue({
      items: [{
        id: 'image-1',
        title: '北京合作学校',
        thumbnailUrl: '/api/images/image-1/thumbnail',
      }],
      hasMore: false,
      nextCursor: null,
    });
    mocks.assignChannelFolder.mockReset().mockResolvedValue(1);
    mocks.createChannelFolder.mockReset().mockResolvedValue(undefined);
    mocks.deleteChannelFolder.mockReset().mockResolvedValue(undefined);
    mocks.renameChannelFolder.mockReset().mockResolvedValue(undefined);
  });

  afterEach(cleanup);

  it('adjusts images inside the current folder without returning to all channel images', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <ChannelImagesPane
            channel="合作案例"
            folders={folders}
            selectedFolderId="folder-beijing"
          />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await screen.findByText('北京合作学校');
    fireEvent.click(screen.getByRole('button', { name: '调整当前分类' }));

    const scope = screen.getByRole('combobox', { name: '要调整的图片范围' });
    expect((scope as HTMLSelectElement).value).toBe('current');
    await waitFor(() => {
      expect(mocks.fetchImages).toHaveBeenLastCalledWith(expect.objectContaining({
        channel: '合作案例',
        folderId: 'folder-beijing',
      }));
    });
    expect(mocks.fetchImages.mock.lastCall?.[0]).not.toHaveProperty('unfiled');

    fireEvent.click(await screen.findByRole('checkbox'));
    fireEvent.change(screen.getByRole('combobox', { name: '图片要归入的分类' }), {
      target: { value: 'folder-shanghai' },
    });
    fireEvent.click(screen.getByRole('button', { name: '归类选中的 1 张' }));

    await waitFor(() => {
      expect(mocks.assignChannelFolder).toHaveBeenCalledWith(
        '合作案例',
        ['image-1'],
        'folder-shanghai',
      );
    });
  });

  it('deletes a parent classification with all descendants after confirmation', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const onSelect = vi.fn();
    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <ChannelFolderTree
            channel="合作案例"
            folders={[
              { id: 'beijing', name: '北京', parentId: null },
              { id: 'chaoyang', name: '朝阳', parentId: 'beijing' },
              { id: 'school', name: '望京学校', parentId: 'chaoyang' },
            ]}
            selectedFolderId={null}
            onSelect={onSelect}
          />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole('button', { name: '删除北京及其下级分类' }));
    expect(await screen.findByText('删除“北京”及其下级分类？')).toBeTruthy();
    expect(screen.getByText(/将同时删除 2 个下级分类/)).toBeTruthy();
    expect(screen.getByText(/图片不会被删除/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '确认删除' }));

    await waitFor(() => {
      expect(mocks.deleteChannelFolder).toHaveBeenCalledWith('beijing');
    });
    expect(onSelect).toHaveBeenCalledWith(null);
  });
});
