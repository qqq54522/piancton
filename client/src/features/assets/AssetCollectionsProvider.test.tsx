// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { assetCollectionQueryKeys } from './assetCollectionQueryKeys';
import { AssetCollectionsProvider, useAssetCollections } from './AssetCollectionsProvider';

const mocks = vi.hoisted(() => ({
  boards: [] as Array<{
    id: string;
    name: string;
    itemCount: number;
    createdAt: string;
    updatedAt: string;
  }>,
  addAssetToBoard: vi.fn(),
  createCollectionBoard: vi.fn(),
  fetchAssetMembership: vi.fn(),
  removeAssetFromBoard: vi.fn(),
}));

vi.mock('@client/src/lib/auth', () => ({
  useAuth: () => ({ user: { role: 'business' } }),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('@client/src/api/assetCollections', () => ({
  addAssetToBoard: mocks.addAssetToBoard,
  createCollectionBoard: mocks.createCollectionBoard,
  fetchAssetCollectionSummary: vi.fn(async () => ({
    likedAssetGroupIds: [],
    likedCount: 0,
    boards: [...mocks.boards],
  })),
  fetchAssetMembership: mocks.fetchAssetMembership,
  likeAsset: vi.fn(),
  removeAssetFromBoard: mocks.removeAssetFromBoard,
  unlikeAsset: vi.fn(),
}));

const board = (id: string, name: string) => ({
  id,
  name,
  itemCount: 0,
  createdAt: '2026-09-16T00:00:00Z',
  updatedAt: '2026-09-16T00:00:00Z',
});

function OpenPickerButton() {
  const collections = useAssetCollections();
  return (
    <button
      type="button"
      onClick={() => collections.openBoardPicker({
        assetGroupId: 'asset-group-1',
        imageId: 'image-1',
        title: '新疆合作案例',
        source: 'library_browse',
      })}
    >
      打开收藏
    </button>
  );
}

function renderProvider(queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } },
})) {
  render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <AssetCollectionsProvider>
          <OpenPickerButton />
        </AssetCollectionsProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  return queryClient;
}

describe('AssetCollectionsProvider board picker', () => {
  afterEach(cleanup);

  beforeEach(() => {
    mocks.boards.splice(0);
    mocks.addAssetToBoard.mockReset().mockResolvedValue({
      assetGroupId: 'asset-group-1',
      liked: false,
      boardIds: ['board-1'],
    });
    mocks.createCollectionBoard.mockReset();
    mocks.fetchAssetMembership.mockReset().mockResolvedValue({
      assetGroupId: 'asset-group-1',
      liked: false,
      boardIds: [],
    });
    mocks.removeAssetFromBoard.mockReset();
  });

  it('refreshes the My Collections cache when the first board is created from an image', async () => {
    const newBoard = board('board-1', '新疆案例');
    mocks.createCollectionBoard.mockImplementation(async () => {
      mocks.boards.push(newBoard);
      return newBoard;
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } },
    });
    queryClient.setQueryData(assetCollectionQueryKeys.boards, []);
    renderProvider(queryClient);

    fireEvent.click(screen.getByRole('button', { name: '打开收藏' }));
    await screen.findByRole('dialog', { name: '收藏到画板' });

    const input = screen.getByRole('textbox', { name: '新画板名称' });
    const selectionLabel = screen.getByText('选择一个画板');
    expect(input.compareDocumentPosition(selectionLabel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    fireEvent.change(input, { target: { value: '新疆案例' } });
    fireEvent.click(screen.getByRole('button', { name: '新建' }));

    await screen.findByText('新疆案例');
    expect(mocks.addAssetToBoard).not.toHaveBeenCalled();
    expect(queryClient.getQueryState(assetCollectionQueryKeys.boards)?.isInvalidated).toBe(true);

    fireEvent.click(screen.getByRole('button', { name: '确定收藏' }));
    await waitFor(() => {
      expect(mocks.addAssetToBoard).toHaveBeenCalledWith(
        'board-1',
        'asset-group-1',
        expect.objectContaining({ imageId: 'image-1' }),
      );
    });
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  });

  it('waits for confirmation before saving to an existing board', async () => {
    mocks.boards.push(board('board-2', '重点素材'));
    renderProvider();

    fireEvent.click(screen.getByRole('button', { name: '打开收藏' }));
    const boardButton = await screen.findByRole('button', { name: /重点素材/ });
    fireEvent.click(boardButton);

    expect(boardButton.getAttribute('aria-pressed')).toBe('true');
    expect(mocks.addAssetToBoard).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: '确定收藏' }));
    await waitFor(() => expect(mocks.addAssetToBoard).toHaveBeenCalledTimes(1));
  });

  it('requires explicit confirmation before removing an image from a board', async () => {
    mocks.boards.push(board('board-3', '已收藏素材'));
    mocks.fetchAssetMembership.mockResolvedValue({
      assetGroupId: 'asset-group-1',
      liked: false,
      boardIds: ['board-3'],
    });
    mocks.removeAssetFromBoard.mockResolvedValue({
      assetGroupId: 'asset-group-1',
      liked: false,
      boardIds: [],
    });
    renderProvider();

    fireEvent.click(screen.getByRole('button', { name: '打开收藏' }));
    const boardButton = await screen.findByRole('button', { name: /已收藏素材/ });
    await screen.findByText('已收藏');
    fireEvent.click(boardButton);

    expect(mocks.removeAssetFromBoard).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '从该画板移除' }));

    await waitFor(() => {
      expect(mocks.removeAssetFromBoard).toHaveBeenCalledWith(
        'board-3',
        'asset-group-1',
        expect.objectContaining({ imageId: 'image-1' }),
      );
    });
  });
});
