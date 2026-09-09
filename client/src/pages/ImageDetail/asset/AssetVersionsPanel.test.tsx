// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { AssetGroup } from '@client/src/types/api';
import AssetVersionsPanel from './AssetVersionsPanel';

const group = {
  id: 'group-1',
  title: '合作案例',
  primaryImageId: 'vertical',
  approvalStatus: 'approved',
  publishStatus: 'published',
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

describe('AssetVersionsPanel', () => {
  it('treats the opened version as the current main view and switches both ways', () => {
    const onImageSelected = vi.fn();
    const actions = {
      addVariant: { isPending: false, mutateAsync: vi.fn() },
      replacePrimary: { isPending: false, mutateAsync: vi.fn() },
      deleteVariant: { isPending: false, mutateAsync: vi.fn() },
    } as never;

    render(
      <AssetVersionsPanel
        group={group}
        currentImageId="horizontal"
        editable
        actions={actions}
        onImageSelected={onImageSelected}
      />,
    );

    expect(screen.getByText('当前查看')).toBeTruthy();
    expect(screen.getByText('素材组封面')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '查看版本“竖版”' }));
    expect(onImageSelected).toHaveBeenCalledWith('vertical');
  });
});
