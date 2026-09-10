// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { AssetGroup } from '@client/src/types/api';
import AssetFilterMetadataPanel from './AssetFilterMetadataPanel';

vi.mock('@client/src/api/image', () => ({
  fetchImageChannels: vi.fn().mockResolvedValue({ channels: ['服务器渠道'] }),
}));

const group = {
  id: 'group-1',
  title: '合作案例',
  primaryImageId: 'vertical',
  approvalStatus: 'approved',
  publishStatus: 'published',
  styleLabel: '旧风格',
  isSceneImage: false,
  createdBy: 'designer',
  images: [
    {
      id: 'vertical',
      title: '竖版',
      fileName: 'vertical.png',
      thumbnailUrl: '/api/images/vertical/thumbnail',
      contentUrl: '/api/images/vertical/content',
      downloadUrl: '/api/images/vertical/download',
      assetRole: 'primary',
      channel: 'PPT',
      versionNo: 1,
      isCurrent: true,
    },
    {
      id: 'horizontal',
      title: '横版',
      fileName: 'horizontal.png',
      thumbnailUrl: '/api/images/horizontal/thumbnail',
      contentUrl: '/api/images/horizontal/content',
      downloadUrl: '/api/images/horizontal/download',
      assetRole: 'derivative',
      channel: '自定义横版渠道',
      versionNo: 2,
      isCurrent: true,
    },
  ],
  conceptLinks: [],
  searchPhrases: [],
  sourceLinks: [],
  createdAt: '2026-09-09T00:00:00Z',
  updatedAt: '2026-09-09T00:00:00Z',
} as AssetGroup;

describe('AssetFilterMetadataPanel', () => {
  beforeEach(() => window.localStorage.clear());

  it('edits the opened version channel and shared group filters', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    const actions = {
      updateFilterMetadata: { isPending: false, mutateAsync },
    } as never;

    renderPanel(actions);

    expect(screen.getByRole('button', { name: '自定义横版渠道' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'PPT' }));
    fireEvent.change(screen.getByPlaceholderText('例如：官网风格、数据卡片、轻插画'), {
      target: { value: '数据卡片' },
    });
    fireEvent.click(screen.getByRole('switch', { name: '场景图' }));
    fireEvent.click(screen.getByRole('button', { name: '保存筛选信息' }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({
      imageId: 'horizontal',
      channel: '自定义横版渠道、PPT',
      styleLabel: '数据卡片',
      isSceneImage: true,
    }));
  });

  it('shows channels loaded from the shared server catalog', async () => {
    const actions = {
      updateFilterMetadata: { isPending: false, mutateAsync: vi.fn() },
    } as never;

    renderPanel(actions);

    expect(await screen.findByRole('button', { name: '服务器渠道' })).toBeTruthy();
  });
});

function renderPanel(actions: never) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={client}>
      <AssetFilterMetadataPanel
        group={group}
        currentImageId="horizontal"
        actions={actions}
      />
    </QueryClientProvider>,
  );
}
